"""Prints Table X containing the precision and recall for the validation set alignment using all five idioms as the pivot idiom and the consensus dataset"""

import pandas as pd


def filter_table(df_full, metric):
    # filter dataframe
    filtered_df = df_full[
        (df_full["metric"] == metric)
        & (df_full["strict_lax"] == "strict")
        & (
            ((df_full["model"] == "gemini-embedding") & (df_full["input"] == "concat"))
            | ((df_full["model"] == "cohere-v4") & (df_full["input"] == "text"))
            | ((df_full["model"] == "voyage-v3") & (df_full["input"] == "concat"))
        )
    ]

    # Step 2: Create a new column to distinguish models
    filtered_df["model_input"] = (
        filtered_df["model"] + " (" + filtered_df["input"] + ")"
    )

    # Step 3: Pivot the table
    out_table = (
        filtered_df.pivot_table(
            index="model_input", columns="pivot", values="score", aggfunc="mean"
        )
        .reset_index()
        .round(3)
    )

    return out_table


def print_latex(prec_table, rec_table, f1_table):
    # Print as a table for markdown
    print(
        "    & Sursilvan & Sutsilvan & Surmiran & Puter & Vallader & Consensus \\\\ \\midrule"
    )
    for i, _ in enumerate(prec_table.iterrows()):
        if i != len(prec_table) - 1:
            print(
                f"{prec_table.iloc[i]['model_input']} & {prec_table.iloc[i]['sursilv']*100:.1f}/{rec_table.iloc[i]['sursilv']*100:.1f}/{f1_table.iloc[i]['sursilv']*100:.1f} & {prec_table.iloc[i]['sutsilv']*100:.1f}/{rec_table.iloc[i]['sutsilv']*100:.1f}/{f1_table.iloc[i]['sutsilv']*100:.1f} & {prec_table.iloc[i]['surmiran']*100:.1f}/{rec_table.iloc[i]['surmiran']*100:.1f}/{f1_table.iloc[i]['surmiran']*100:.1f} & {prec_table.iloc[i]['puter']*100:.1f}/{rec_table.iloc[i]['puter']*100:.1f}/{f1_table.iloc[i]['puter']*100:.1f} & {prec_table.iloc[i]['vallader']*100:.1f}/{rec_table.iloc[i]['vallader']*100:.1f}/{f1_table.iloc[i]['vallader']*100:.1f} & {prec_table.iloc[i]['consensus']*100:.1f}/{rec_table.iloc[i]['consensus']*100:.1f}/{f1_table.iloc[i]['consensus']*100:.1f} \\\\"
            )
        else:
            print(
                f"{prec_table.iloc[i]['model_input']} & {prec_table.iloc[i]['sursilv']*100:.1f}/{rec_table.iloc[i]['sursilv']*100:.1f}/{f1_table.iloc[i]['sursilv']*100:.1f} & {prec_table.iloc[i]['sutsilv']*100:.1f}/{rec_table.iloc[i]['sutsilv']*100:.1f}/{f1_table.iloc[i]['sutsilv']*100:.1f} & {prec_table.iloc[i]['surmiran']*100:.1f}/{rec_table.iloc[i]['surmiran']*100:.1f}/{f1_table.iloc[i]['surmiran']*100:.1f} & {prec_table.iloc[i]['puter']*100:.1f}/{rec_table.iloc[i]['puter']*100:.1f}/{f1_table.iloc[i]['puter']*100:.1f} & {prec_table.iloc[i]['vallader']*100:.1f}/{rec_table.iloc[i]['vallader']*100:.1f}/{f1_table.iloc[i]['vallader']*100:.1f} & {prec_table.iloc[i]['consensus']*100:.1f}/{rec_table.iloc[i]['consensus']*100:.1f}/{f1_table.iloc[i]['consensus']*100:.1f} \\\\ \\bottomrule"
            )


if __name__ == "__main__":
    # Load full evaluation for all models using text, html, and embconcat as input format
    df_text = pd.read_csv("../align/eval/pivot_2_text.csv")
    df_html = pd.read_csv("../align/eval/pivot_2_html.csv")
    df_concat = pd.read_csv("../align/eval/pivot_2_embconcat.csv")

    # Load evaluation of the consensus merge for the best performing models in the greedy alignment task
    df_consensus = pd.read_csv("../align/eval/consensus_eval_new.csv")

    # Add a column corresponding to input type
    df_text["input"] = "text"
    df_html["input"] = "html"
    df_concat["input"] = "concat"
    df_consensus["input"] = df_consensus["model"].apply(
        lambda x: "text" if x == "cohere-v4" else "concat"
    )

    # Concatenate
    df_full = pd.concat([df_text, df_html, df_concat, df_consensus])

    prec_table = filter_table(df_full, "precision")
    rec_table = filter_table(df_full, "recall")
    f1_table = filter_table(df_full, "f1")

    print_latex(prec_table, rec_table, f1_table)
