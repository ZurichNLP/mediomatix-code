#!/bin/bash
#A bash script for a simple cosine-sim alignment strategy on the val set to test which model we should focus on 

idioms=("sursilv" "sutsilv" "surmiran" "puter" "vallader")

#Print header
echo "Model,Idioms,Input,Proportion Correct" > ./greedy_align_stats.csv

for input in text html embconcat
do
    for model in cohere-v4 sentence-swissbert qwen3-Embedding-0.6B openai-v3 voyage-v3 gemini-embedding
    do
        echo "---${model}---"
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
                #align and append to out file
                python3 ./greedy_align.py --model $model --src $src --tgt $tgt --input $input>> ./greedy_align_stats.csv
            done 
        done
    done
done