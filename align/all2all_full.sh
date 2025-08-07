#!/bin/bash

#all to all for the full data ; first arg should be the grade level

#get to vecalign repo
cd ../../vecalign

emb_path="/projects/text/romansh/textbooks/final/embeddings"
overlap_path="/projects/text/romansh/textbooks/final/overlaps"

idioms=("sursilv" "sutsilv" "surmiran" "puter" "vallader")

#Output dir
mkdir /projects/text/romansh/textbooks/final/all2all
OUTDIR="/projects/text/romansh/textbooks/final/all2all"

grade=$1

#Align embeddings from all books in this grade
for full_path in "$overlap_path"/"${grade}"*; 
do
    book=$(basename "$full_path")
    mkdir ${OUTDIR}/${book}
    echo "---${book}---"
    #loop through ls contents of the dir
    for chap in $(ls ${emb_path}/${book})
    do
    echo "---${chap}---"
    mkdir ${OUTDIR}/${book}/${chap}
    #loop through range 0 to 4 (we have 5 idioms)
    for i in "${!idioms[@]}"
    do
        #to get the target idiom, loop through the idioms that i hasn't covered yet (i.e., if i is on idiom 2 (surmiran) only loop through 3 and 4 (puter and vallader) as tgts)
        for j in $(seq $((i+1)) $((${#idioms[@]} - 1)))
        do
            #index the array of idioms using i for the source and j for the unseen targets. 
            src=${idioms[$i]}
            tgt=${idioms[$j]}
            echo "Aligning $src to $tgt"

            src_text="/projects/text/romansh/textbooks/final/texts/${book}/${chap}/rm-${src}_text.txt"
            tgt_text="/projects/text/romansh/textbooks/final/texts/${book}/${chap}/rm-${tgt}_text.txt"
            src_emb="${emb_path}/${book}/${chap}/rm-${src}_text_overlaps.emb"
            tgt_emb="${emb_path}/${book}/${chap}/rm-${tgt}_text_overlaps.emb"
            src_overlaps="${overlap_path}/${book}/${chap}/rm-${src}_text_overlaps.txt"
            tgt_overlaps="${overlap_path}/${book}/${chap}/rm-${tgt}_text_overlaps.txt"

            # Check all required files exist
            if [[ -f "$src_text" && -f "$tgt_text" && -f "$src_emb" && -f "$tgt_emb" && -f "$src_overlaps" && -f "$tgt_overlaps" ]]; then
                echo "Aligning $src to $tgt"
                ./vecalign.py --alignment_max_size=2 \
                    --src "$src_text" \
                    --tgt "$tgt_text" \
                    --src_embed "$src_overlaps" "$src_emb" \
                    --tgt_embed "$tgt_overlaps" "$tgt_emb" \
                    > "${OUTDIR}/${book}/${chap}/${src}-${tgt}_align.txt"
            else
                echo "Skipping $src–$tgt in $book/$chap — missing files"
            fi
        done
    done    
    done
done