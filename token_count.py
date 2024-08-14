from finetune import PythonDataset
from datasets import load_from_disk
from spy import Transformer
from tokenizers import Tokenizer
import transformers
import tqdm
import re
import huggingface_hub
huggingface_hub.login(token='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')

import tiktoken



dataset = load_from_disk('./cached/starcoderdata_100star')
transformer = Transformer()
# re to remove the first line of the code
re_first_line = re.compile(r'^.*\n')
passed_so_far = 0
py2_skipped = 0
oneline_skipped = 0
error_counts = 0

print(transformer.special_tokens)
for model in ['codex', 'Salesforce/codegen-350M-mono', 'bigcode/santacoder', 'Salesforce/codegen2-7B', 'bigcode/starcoder', 'microsoft/codebert-base', 'Salesforce/codet5p-16b', 'Salesforce/codet5-large', 'replit/replit-code-v1_5-3b', 'facebook/incoder-6B', 'WizardLM/WizardCoder-Python-34B-V1.0', 'codellama/CodeLlama-7b-Python-hf', "deepseek-ai/deepseek-coder-6.7b-base",'gpt4','gpt2']:
    if model == 'gpt4':
        tokenizer = tiktoken.encoding_for_model("gpt-4")
        tokenizer = tiktoken.Encoding(
            # If you're changing the set of special tokens, make sure to use a different name
            # It should be clear from the name what behaviour to expect.
            name="gpt4-spy",
            pat_str=tokenizer._pat_str,
            mergeable_ranks=tokenizer._mergeable_ranks,
            special_tokens={
                **tokenizer._special_tokens,
                **{v: i+100264 for i,v in enumerate(transformer.special_tokens)}
            }
        )
    elif model == 'codex':
        tokenizer = tiktoken.encoding_for_model("code-davinci-002")
        tokenizer = tiktoken.Encoding(
            # If you're changing the set of special tokens, make sure to use a different name
            # It should be clear from the name what behaviour to expect.
            name="codex-spy",
            pat_str=tokenizer._pat_str,
            mergeable_ranks=tokenizer._mergeable_ranks,
            special_tokens={
                **tokenizer._special_tokens,
                **{v: i+50281 for i,v in enumerate(transformer.special_tokens)}
            }
        )
    else:
        tokenizer = transformers.AutoTokenizer.from_pretrained(model, trust_remote_code=True)
        tokenizer.add_special_tokens({'additional_special_tokens': transformer.special_tokens})
        # tokenizer.add_tokens(transformer.special_tokens)
    code_tokens = 0
    filtered_code_tokens = 0
    parsed_tokens = 0
    failed = []
    for sample in tqdm.tqdm(dataset['content'][:1000]):
        origin_code_len = len(tokenizer.encode(sample, allowed_special=set(['<|endoftext|>'] + list(tokenizer._special_tokens.keys())))) if model in ['gpt4','codex'] else len(tokenizer.encode(sample))
        code_tokens += origin_code_len
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
        current_parsed_len = len(tokenizer.encode(spy_code, allowed_special=set(['<|endoftext|>'] + list(tokenizer._special_tokens.keys())))) if model in ['gpt4','codex']  else len(tokenizer.encode(spy_code))
        parsed_tokens+=current_parsed_len
        filtered_code_tokens += origin_code_len
        
    print(f'Model: {model}, Code Tokens: {code_tokens}, Filtered Code Tokens: {filtered_code_tokens}, Parsed Tokens: {parsed_tokens}')
    print(f'Parsed / Filtered: {parsed_tokens/filtered_code_tokens}')
    
    with open('./results/token_count.csv', 'a+') as f:
        f.write(f'{model},{code_tokens},{filtered_code_tokens},{parsed_tokens}, {parsed_tokens/filtered_code_tokens}\n')