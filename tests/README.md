# Testing

In development, these commands are what is assumed to have been run


**bam** mode

### vanilla hg19 with peaks
```
bap bam -i data/test.small.bam -z -bt CB -ji 0.002 -em -pf data/test.small.peaks.bed 
```

### testing species mixing
```
 bap bam -i data/small_mix.bam -bt XB -ji 0.0001 -r hg19-mm10 -z --mapq 0 -bf 100 -cf 100
```

## debarcoding
```
bap-barcode v1.0 -a fastq_br/biorad_v1_R1.fastq.gz -b fastq_br/biorad_v1_R2.fastq.gz --nmismatches 1
bap-barcode v2.1 -a fastq_br/biorad_v2_R1.fastq.gz -b fastq_br/biorad_v2_R2.fastq.gz --nmismatches 1
bap-barcode v2.1-multi -a fastq_br/biorad_v2-multi_R1.fastq.gz -b fastq_br/biorad_v2-multi_R2.fastq.gz --nmismatches 1


bwa mem /Volumes/dat/genomes/hg19_bwa/hg19.fa debarcode-c001_1.fastq.gz debarcode-c001_2.fastq.gz | samtools view -bS - |  samtools sort -@ 4 - -o debarcode.bam
```

## debarcoding 10X data
```
bap-barcode 10X-v1 -a fastq_10X/test-10X_R1.fastq.gz -b fastq_10X/test-10X_R3.fastq.gz -i fastq_10X/test-10X_R2.fastq.gz -o testbap-10x
```


### others

This is for running individual pieces of the pipeline

*step 11*
```
python ../bap/bin/python/11_quantBarcode_Filt.py --input data/small_hg19.bam --bedtools-genome ../bap/anno/bedtools/chrom_hg19.sizes --barcode-tag XB -n h -o data

```
