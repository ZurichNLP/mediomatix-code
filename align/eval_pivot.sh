#!/bin/bash

#first argument should be the column name that should be evaluated
#e.g., for evaluating alignments based on the extracted text embeddings ./eval_pivot.sh text 

mkdir ./eval

#Get to vecalign repo
cd ../../vecalign

gold_path="../textbooks/align/ground_truth"
hyp_path="/projects/text/romansh/textbooks/val_align_pivot/align_02/${1}"

idioms=("sursilv" "sutsilv" "surmiran" "puter" "vallader")

#Goal: print the following rows to a csv: embedding model, pivot, idioms, chapter, metric, strict_lax, score

#header
echo "model,pivot,idioms,chapter,metric,strict_lax,score">"../textbooks/align/eval/pivot_2_${1}.csv"

for model in cohere-v4 sentence-swissbert qwen3-Embedding-0.6B openai-v3 voyage-v3 gemini-embedding
do
    echo "---${model}---"
    #loop through ls contents of the dir
    for chap in $(ls ${gold_path})
    do
        echo "---${chap}---"

        for p in "${!idioms[@]}"
        do  
            #index array of idioms to get the pivot idiom
            pivot=${idioms[$p]}

            #loop through range 0 to 4 (we have 5 idioms)
            for i in "${!idioms[@]}"
            #This will evaluate the Vecalign alignments with the pivot as well as the inferred alignments
            do
                #to get the target idiom, loop through the idioms that i hasn't covered yet (i.e., if i is on idiom 2 (surmiran) only loop through 3 and 4 (puter and vallader) as tgts)
                for j in $(seq $((i+1)) $((${#idioms[@]} - 1)))
                do
                    #index the array of idioms using i for the source and j for the unseen targets. 
                    src=${idioms[$i]}
                    tgt=${idioms[$j]}
                    echo "Evaluating $src to $tgt with a $pivot pivot"
                    #Run eval and append to the csv
                    python3 score_rom.py -t "${hyp_path}/${model}/${chap}/${pivot}/${src}-${tgt}_align.txt" -g "${gold_path}/${chap}/${src}-${tgt}_2_gold.txt" \
                    --model ${model} --idiom_pair "${src}-${tgt}" --chapter_name ${chap} --pivot ${pivot} >> "../textbooks/align/eval/pivot_2_${1}.csv"
                done
            done
        done    
    done
done
