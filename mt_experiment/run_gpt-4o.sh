idioms=("rm_sursilv" "rm_sutsilv" "rm_surmiran" "rm_puter" "rm_vallader")
for src in "${idioms[@]}"; do
  for tgt in "${idioms[@]}"; do
    if [ "$src" != "$tgt" ]; then
      python run_translate.py --system=GPT-4o --lp=${src}-${tgt} --no_testsuites
    fi
  done
done
