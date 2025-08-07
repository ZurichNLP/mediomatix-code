#!/bin/bash
#Argument one: Model
# Example Call
# ./eval_consensus.sh cohere-v4 

mkdir ./eval

#Get to vecalign repo
cd ../../vecalign

model="${1}"

gold_path="../textbooks/align/ground_truth"

hyp_path="/projects/text/romansh/textbooks/val_test/align_02/text"

idioms=("sursilv" "sutsilv" "surmiran" "puter" "vallader")

#Goal: print the following rows to a csv: embedding model, pivot, idioms, chapter, metric, strict_lax, score

#header if the file doesn't exist
if [ ! -f "../textbooks/align/eval/consensus_eval_new.csv" ]; then
    echo "model,pivot,idioms,chapter,metric,strict_lax,score" > "../textbooks/align/eval/consensus_eval_new.csv"
fi

echo "---${model}---"
#loop through ls contents of the dir
for chap in $(ls ${gold_path})
do
    echo "---${chap}---"

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
            python3 score_rom.py -t "${hyp_path}/${model}/${chap}/consensus/${src}-${tgt}_align.txt" -g "${gold_path}/${chap}/${src}-${tgt}_2_gold.txt" \
            --model ${model} --idiom_pair "${src}-${tgt}" --chapter_name ${chap} --pivot "consensus" >> "../textbooks/align/eval/consensus_eval_new.csv"
        done
    done
done

