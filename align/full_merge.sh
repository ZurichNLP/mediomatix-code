#!/bin/bash

#First argument: grade level

base_dir="/projects/text/romansh/textbooks/final/TEST"
grade=$1

for full_path in "$base_dir"/"${grade}"*; 
do
    book=$(basename "$full_path")
    echo "---Processing book: ${book}---"
    python3 ./merge_pivots.py --book="${book}" --store_pairwise
done