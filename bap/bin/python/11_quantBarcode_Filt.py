import sys
import re
import pysam
import shutil
import os 

from multiprocessing import Pool
from optparse import OptionParser
from collections import Counter
from contextlib import contextmanager

opts = OptionParser()
usage = "usage: %prog [options] [inputs] Script to process aligned .bam files to 1) filter based on prevalent cell barcodes;  2) split based on valid chromosomes; and 3) filter for unique fragments (at the barcode level)"
opts = OptionParser(usage=usage)

opts.add_option("--input", "-i", help="Name of the .bam file to parse")
opts.add_option("--name", "-n", help="Name of the set of .bam files to collate")
opts.add_option("--output", "-o", help="Path to the output directory for these")

opts.add_option("--mapq", default = 30, help="Minimum mapq for a read to be kept")

opts.add_option("--barcode-tag", default = 'CB', help="Name of the first .bam file")
opts.add_option("--min-fragments", default = 100, help="Minimum number of fragments for barcode consideration")
opts.add_option("--bedtools-genome", help="Filepath to bedtools genome.")
opts.add_option("--min_chromosome_size", default = 1000000, help="Minimum chromosome size (in bp) to be considered for fragment overlap analysis.")
opts.add_option("--ncores", default = 4, help="Number of cores for parallel processing.")

options, arguments = opts.parse_args()

bamname = options.input
name = options.name
out = options.output

minmapq = float(options.mapq)
barcodeTag = options.barcode_tag
minFrag = int(options.min_fragments)
bedtoolsGenomeFile = options.bedtools_genome
minChromosomeSize = int(options.min_chromosome_size)
cpu = int(options.ncores)

def listDictToCounter(lst):
	dct = Counter()
	for d in lst:
		for k, v in d.items():
			dct[k] += v 
	return(dct)

def getBarcode(intags):
	'''
	Parse out the barcode per-read
	'''
	for tg in intags:
		if(barcodeTag == tg[0]):
			return(tg[1])
	return("NA")

#---------------------------------------------------------------
# Function for extracting barcodes corresponding to unique reads
#---------------------------------------------------------------
def getUniqueBarcodes(chrom):
	
	# Use dictionary logic
	barcodes = dict()
	barcodes_all = dict()
	
	# Keep track of the base pair for indexing unique reads
	barcode_bp = ['NA']
	bp = 0

	bam = pysam.AlignmentFile(bamname,'rb')
	Itr = bam.fetch(str(chrom),multiple_iterators=True)
	
	for read in Itr:
		if(read.mapping_quality > minmapq):
			read_barcode = getBarcode(read.tags)
			barcodes_all[read_barcode] = barcodes_all.get(read_barcode, 0) + 1
	
			# New base pair -- no duplicates
			if(read.reference_start != bp):
				bp = read.reference_start
				barcode_bp = [read_barcode]
				barcodes[read_barcode] = barcodes.get(read_barcode, 0) + 1
	
			# Same base pair -- verify that it's not existing barcodes
			else:
				if( not read_barcode in barcode_bp):
					barcodes[read_barcode] = barcodes.get(read_barcode, 0) + 1
					barcode_bp.append(read_barcode)
	return(barcodes, barcodes_all)


#---------------------------------------------------------
# Function for writing unique reads for barcodes that pass
#---------------------------------------------------------
def writeUniquePassingReads(chrom):
	
	# the bc variable is in the global environment
	
	# Keep track of the base pair for indexing unique reads
	barcode_bp = ['NA']
	bp = 0
	idx = chrs.index(chrom)
	file = fopen[idx]
	
	# Iterate through bam file
	bam = pysam.AlignmentFile(bamname,'rb')
	Itr = bam.fetch(str(chrom),multiple_iterators=True)
	for read in Itr:
		if(read.mapping_quality > minmapq):
			read_barcode = getBarcode(read.tags)
			
			# New base pair -- no duplicates; write out and update
			if(read.reference_start != bp and read_barcode in bc):
				bp = read.reference_start
				barcode_bp = [read_barcode]
				file.write(read)
				
				# Same base pair -- verify that it's not existing barcodes
			else:
				# Still at the same base pair; verify that we haven't seen this barcode before
				if( not read_barcode in barcode_bp and read_barcode in bc):
					barcode_bp.append(read_barcode)
					file.write(read)
	bam.close()
	return(chrom)

# Handle the chromosomes
chrlens = {}
with open(bedtoolsGenomeFile) as f:
	for line in f:
		tok = line.split("\t")
		chrlens[tok[0]] = tok[1].strip()

# Split into those that are short (mitochondria) and long (nuclear)
chrlenfail = {x : chrlens[x] for x in chrlens if int(chrlens[x]) < minChromosomeSize }
chrsOther = list(chrlenfail.keys())

chrlenpass = {x : chrlens[x] for x in chrlens if int(chrlens[x]) >= minChromosomeSize }
chrs = list(chrlenpass.keys())

bamchrfiles = [out + "/" + name + "." + chr + ".bam" for chr in chrs]
bamchrrouter = open(out.replace("temp/filt_split", ".internal/samples") + "/" + name + ".chrbam.txt", "w") 
for v in bamchrfiles:
	bamchrrouter.write(v+"\n")
bamchrrouter.close() 

	
# Quantify the barcodes into a list of dictionaries
pool = Pool(processes=cpu)
unique_barcodes, all_barcodes = zip(*pool.map(getUniqueBarcodes, chrs))
pool.close()

unique_barcodes = listDictToCounter(unique_barcodes)
all_barcodes = listDictToCounter(all_barcodes)

# Quantify read numbers for short chromosomes ==> mitochondria
pool = Pool(processes=cpu)
unique_bc_short, all_bc_short = zip(*pool.map(getUniqueBarcodes, chrsOther))
pool.close()
unique_bc_short = listDictToCounter(unique_bc_short)
all_bc_short = listDictToCounter(all_bc_short)

# Flatten list and determine barcodes passing filter
barcodes = {x : unique_barcodes[x] for x in unique_barcodes if unique_barcodes[x] >= minFrag and x != "NA"}
global bc
bc = list(barcodes.keys())

#-------
# Loop back through, filter for positive barcodes, split by chr
#-------

# Function to open lots of files
@contextmanager
def multi_file_manager(files, mode='rt'):
	"""
	Open multiple files and make sure they all get closed.
	"""
	temp = pysam.AlignmentFile(bamname, "rb")
	files = [pysam.AlignmentFile(file, "wb", template = temp) for file in files]
	temp.close()
	yield files
	for file in files:
		file.close()
	
# Final loop to write out passing reads
with multi_file_manager(bamchrfiles) as fopen:
	pool = Pool(processes=cpu)
	toy_out = pool.map(writeUniquePassingReads, chrs)
	pool.close()

# Write out barcode file
bcfile = open(out.replace("temp/filt_split", "final") + "/" + name + ".barcodequants.csv", "w") 
bcfile.write("Barcode,UniqueNuclear,TotalNuclear,TotalMito"+ "\n")
for k, v in barcodes.items():
	if(all_bc_short.get(k) == None):
		mito = 0
	else:
		mito = all_bc_short.get(k)
	bcfile.write(k +","+ str(v)+"," + str(all_barcodes.get(k)) + "," + str(mito) + "\n")
bcfile.close() 

