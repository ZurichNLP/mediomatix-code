#!/bin/bash

# first argument should be the number of overlaps

cd ../../vecalign

for dial in sursilv puter surmiran sutsilv vallader
do
    for book in $(ls /projects/text/romansh/textbooks/final/texts)
    do
        mkdir -p /projects/text/romansh/textbooks/final/overlaps/${book}
        for chap in $(ls /projects/text/romansh/textbooks/final/texts/${book})
        do
            mkdir -p /projects/text/romansh/textbooks/final/overlaps/${book}/${chap}
            infile="/projects/text/romansh/textbooks/final/texts/${book}/${chap}/rm-${dial}_text.txt"
            outfile="/projects/text/romansh/textbooks/final/overlaps/${book}/${chap}/rm-${dial}_text_overlaps.txt"
            # #Get text overlaps
            if [ -f "$infile" ]; then
                # Get text overlaps
                python3 ./overlap.py -i "$infile" -o "$outfile" -n "$1"
            else
                echo "Missing input file: $infile"
            fi
        done
    done
done