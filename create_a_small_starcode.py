from datasets import load_dataset
import re

from spy import Transformer

re_first_line = re.compile(r'^.*\n')
transformer = Transformer()

def convert_to_spy(examples): 
    spy_examples = []
    py_examples = []
    for sample in examples['content']:
        try:
            first_line = re_first_line.match(sample).group()
        except:
            continue

        if first_line.startswith('<'):
            sample = re_first_line.sub('', sample) 

        if sample.startswith('#!/'):
            continue
        try:
            spy_code = transformer.parse(sample)
        except (ValueError, RecursionError):
            continue
        py_examples.append(sample)
        spy_examples.append(spy_code)

    return {'content': spy_examples}

for lang in ['python']:
    dataset = load_dataset('bigcode/starcoderdata', data_dir=lang, split="train", cache_dir="./cached")
    # filter the dataset with stars
    dataset = dataset.filter(lambda example: example['max_stars_count'] > 100)
    dataset.save_to_disk("./cached/starcoderdata_100star")
    
    dataset = dataset.map(convert_to_spy, batched=True, load_from_cache_file=False, remove_columns=['max_stars_repo_path', 'max_stars_repo_name', 'max_stars_count', 'id'])
    dataset.save_to_disk("./cached/starcoderdata_100star_spy")
    print(dataset)


