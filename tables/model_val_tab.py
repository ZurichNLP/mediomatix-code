"""Prints Table X containing the average proportion correct on the greedy alignment task used for deciding on the embedding model and text type (i.e., text v. HTML v. Their concatenation)"""

import pandas as pd

if __name__ == "__main__":
    # Read in the csv with results
    df = pd.read_csv("../val_exp/greedy_align_stats.csv")

    # Group by the mean over all the idiom pairs, for all the models for each input type
    df_final = df.drop(labels="Idioms", axis=1).groupby(["Model", "Input"]).mean()

    df_final = df_final.unstack(level="Input")

    # Print Latex table
    print(" Model & Text & HTML & Concat \\\\ \\midrule")
    for row in df_final.iterrows():
        # print(row[-1][-1])
        print(
            f"{row[0]} & {float(row[1][2])*100:.1f} & {float(row[1][1])*100:.1f} & {float(row[1][0])*100:.1f} \\\\"
        )
