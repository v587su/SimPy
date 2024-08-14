from datasets import load_from_disk
from spy import Transformer
from tokenizers import Tokenizer
from transformers import AutoTokenizer
import tqdm
import time
import huggingface_hub
import tiktoken
import re



re_first_line = re.compile(r'^.*\n')
tokenizer = tiktoken.encoding_for_model("gpt-4")
hug_tokenizer = AutoTokenizer.from_pretrained('bigcode/starcoder', trust_remote_code=True)
dataset = load_from_disk('./cached/starcoderdata_100star')
transformer = Transformer()
records = []
for sample in tqdm.tqdm(dataset['content']):
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

    char_len = len(sample)
    current_time = time.time()
    tokenizer.encode(sample, allowed_special=set(['<|endoftext|>'])) 
    token_time = time.time() - current_time
    tokenized = tokenizer.encode(sample, allowed_special=set(['<|endoftext|>']))

    current_time = time.time()
    tokenizer.decode(tokenized)
    decode_time = time.time() - current_time
    token_num = len(tokenized)

    current_time = time.time()
    hug_tokenizer.encode(sample) 
    hug_token_time = time.time() - current_time
    hug_tokenized = hug_tokenizer.encode(sample)
    
    current_time = time.time()
    hug_tokenizer.decode(hug_tokenized)
    hug_decode_time = time.time() - current_time
    hug_token_num = len(hug_tokenized)

    current_time = time.time()
    transformer.parse(sample)
    parse_time = time.time() - current_time

    current_time = time.time()
    transformer.decode(spy_code)
    parse_back_time = time.time() - current_time

    records.append({
        'char_len': char_len,
        'token_num': token_num,
        'token_time': token_time,
        'parse_time': parse_time,
        'parse_back_time': parse_back_time,
        'hug_token_time': hug_token_time,
        'hug_token_num': hug_token_num,
        'hug_decode_time': hug_decode_time,
        'decode_time': decode_time,
    })

with open('./results/tokenizer_time.csv', 'w') as f:
    f.write('char_len,token_num,token_time,parse_time,parse_back_time,hug_token_time,hug_token_num,hug_decode_time,decode_time\n')
    for record in records:
        f.write(f"{record['char_len']},{record['token_num']},{record['token_time']},{record['parse_time']},{record['parse_back_time']},{record['hug_token_time']},{record['hug_token_num']},{record['hug_decode_time']},{record['decode_time']}\n")


    