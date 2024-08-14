import os
import transformers
import re
from spy import Transformer
from datasets import load_dataset
from utils import get_args
import random
import huggingface_hub
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments, DataCollatorForLanguageModeling


class PythonDataset:
    def __init__(self, tokenizer, dataset, transformer, seq_length=1024, language='python', ratio=1.0):
        self.tokenizer = tokenizer
        self.concat_token_id = tokenizer.eos_token_id if tokenizer.eos_token_id is not None else args.eos_token_id
        # self.dataset = dataset.shard(index=0, num_shards=10000)
        self.dataset = dataset
        self.seq_length = seq_length
        self.transformer = transformer
        self.language = language
        self.re_first_line = re.compile(r'^.*\n')

        if language.startswith('spython'):
            self.dataset = self.dataset.filter(lambda x: random.random() < ratio)

        self.dataset = self.dataset.map(self.convert_to_spy, batched=True, load_from_cache_file=False, remove_columns=['max_stars_repo_path', 'max_stars_repo_name', 'max_stars_count', 'id'])
        self.dataset = self.dataset.map(self.tokenize_and_concate, batched=True, remove_columns=['content'], load_from_cache_file=False)

    def convert_to_spy(self, examples): 
        spy_examples = []
        for sample in examples['content']:
            try:
                first_line = self.re_first_line.match(sample).group()
            except:
                continue

            if first_line.startswith('<'):
                sample = self.re_first_line.sub('', sample) 

            if sample.startswith('#!/'):
                continue
            try:
                spy_code = self.transformer.parse(sample)
            except (ValueError, RecursionError):
                continue

            spy_examples.append(spy_code if self.language.startswith('spython') else sample)

        return {'content': spy_examples}
    

    def tokenize_and_concate(self, examples):
        tokenized_example = self.tokenizer(examples['content'])

        concatenated_examples = {}
        for k in tokenized_example.keys():
            all_token_ids = []
            for tokenized_input in tokenized_example[k]:
                all_token_ids.extend(tokenized_input + [self.concat_token_id])
            concatenated_examples[k] = all_token_ids
          
        total_length = len(concatenated_examples[list(concatenated_examples.keys())[0]])
        result = {k:[] for k in concatenated_examples.keys()}
        for k,t in concatenated_examples.items():
            for i in range(0, total_length, self.seq_length):
                if i+self.seq_length < total_length:
                    result[k].append(t[i:i+self.seq_length])
        return {'input_ids': result['input_ids'], 'labels': result["input_ids"].copy()}


if __name__ == '__main__':
    args = get_args()
    transformer = Transformer()
    tokenizer = AutoTokenizer.from_pretrained(args.model_path, cache_dir="./cached")
    tokenizer.pad_token = tokenizer.eos_token 
    transformer.special_tokens = sorted(list(set(transformer.special_tokens)))
    if args.language.startswith('spython'):
        tokenizer.add_tokens(transformer.special_tokens)
     
    
    model_config = transformers.AutoConfig.from_pretrained(args.model_path, cache_dir="./cached")
    if args.language.startswith('spython'):
        model_vocab_size = model_config.vocab_size + len(transformer.special_tokens)
        
        if model_config.vocab_size > model_vocab_size:
            model_vocab_size = model_config.vocab_size
    elif model_config.vocab_size > tokenizer.vocab_size:
        model_vocab_size = model_config.vocab_size
    else:
        model_vocab_size = tokenizer.vocab_size

    if not args.further_train:
        model = AutoModelForCausalLM.from_pretrained(args.model_path, cache_dir="./cached", load_in_8bit=False, vocab_size=model_vocab_size, ignore_mismatched_sizes=True)
    elif args.from_scratch:
        model = AutoModelForCausalLM.from_config(model_config, vocab_size=model_vocab_size, ignore_mismatched_sizes=True)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.further_train, cache_dir="./cached", load_in_8bit=False, vocab_size=model_vocab_size, ignore_mismatched_sizes=True)

    dataset = load_dataset(args.dataset_name, split="train", cache_dir="./cached")
    dataset = dataset.train_test_split(test_size=0.05, shuffle=True)
    train_dataset = dataset['train']
    val_dataset = dataset['test']
   
    train_data = PythonDataset(tokenizer, train_dataset, transformer, seq_length=args.seq_length, language=args.language, ratio=args.ratio).dataset
    
    val_data = PythonDataset(tokenizer, val_dataset, transformer, seq_length=args.seq_length, language=args.language).dataset

    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer,mlm=False)
  
    if args.further_train:
        run_name = f"{args.model_path.split('/')[-1]}-{args.language}-{args.ratio}"
    else:
        run_name = f"{args.model_path.split('/')[-1]}-{args.language}"

    if args.from_scratch:
        run_name += '-from_scratch'

    training_args = TrainingArguments(
        output_dir=os.path.join(args.output_dir, run_name),
        dataloader_drop_last=True,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        num_train_epochs=args.epoch,
        eval_steps=args.eval_freq,
        save_steps=args.save_freq,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        torch_compile=True,
        lr_scheduler_type=args.lr_scheduler_type,
        warmup_steps=args.num_warmup_steps,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        fp16=True,
        weight_decay=args.weight_decay,
        run_name=run_name,
        logging_steps=args.log_freq,
        log_level='debug',
        ddp_find_unused_parameters=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=train_data, eval_dataset=val_data, data_collator=data_collator)
    print("Training...")
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)
    print("Saving last checkpoint of the model")
    model.save_pretrained(os.path.join(args.output_dir, run_name, 'best_model'))


