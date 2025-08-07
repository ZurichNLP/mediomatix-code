#!/bin/bash
#Move pairwise alignments for a given pivot to the directory where they'll be merged for the multi-parallel dataset. 

#first argument should be the grade level

all2all_path="/projects/text/romansh/textbooks/final/all2all"

idioms=("sursilv" "sutsilv" "surmiran" "puter" "vallader")

grade=$1

#Output dir
mkdir -p /projects/text/romansh/textbooks/final/pivot_align
OUTDIR="/projects/text/romansh/textbooks/final/pivot_align"


for full_path in "$all2all_path"/"${grade}"*; 
do
    book=$(basename "$full_path")
    mkdir -p ${OUTDIR}/${book}
    echo "---${book}---"
    #loop through ls contents of the dir
    for chap in $(ls ${all2all_path}/${book})
    do
    echo "---${chap}---"
    mkdir -p ${OUTDIR}/${book}/${chap}
    #loop through range 0 to 4 (we have 5 idioms)
        for p in "${!idioms[@]}"
        do  
            shopt -s nullglob
            #index array of idioms to get the pivot idiom
            pivot=${idioms[$p]}
            pivot_glob="${all2all_path}/${book}/${chap}/*${pivot}*.txt"
            #Get all the pairwise alignments with the pivot
            pivot_files=($pivot_glob)

            # Skip if no files for this pivot
            if [ ${#pivot_files[@]} -eq 0 ]; then
                echo "Skipping pivot $pivot in $book/$chap — no alignment files found"
                continue
            fi

            mkdir -p ${OUTDIR}/${book}/${chap}/${pivot}

            # Copy the alignment files for this pivot to the output dir
            cp "${pivot_files[@]}" ${OUTDIR}/${book}/${chap}/${pivot}
            
            #Delete pivot from idioms
            temp=()
            for idiom in "${idioms[@]}"; do
                if [[ "$idiom" != "$pivot" ]]; then
                    temp+=("$idiom")
                fi
            done
        done    
    done
done
