
# SimPy
This repository contains the source for the paper "AI Coders Are Among Us: Rethinking Programming Language Grammar Towards Efficient Code Generation".
It consists of the following artifacts:
1. The [tree-sitter](https://tree-sitter.github.io/tree-sitter/creating-parsers#grammar-rules) grammar file for SimPy in the folder `spy_grammar`, which can be used to generate the AST parser for SimPy.
2. The converter for SimPy in the folder `spy`, which can convert between SimPy code and Python code.
3. The scripts to run the experiments in the paper.

##  SimPy Grammar
The grammar specification is in the file `spy_grammar/grammar.js`. You can refer to the [tree-sitter](https://tree-sitter.github.io/tree-sitter/creating-parsers#grammar-rules) documentation for the grammar specification.

## SimPy Convertor
The converter is in the folder `spy`. It can be used by:
```python
from spy import Transformer
transformer = Transformer()
spy_code = transformer.parse('print("Hello World")')
py_code = transformer.decode('<import>ast')
```

## Experiments

### Dataset
The dataset used in the paper is [starcoderdata](https://huggingface.co/datasets/bigcode/starcoderdata).

### Scripts

#### Training

The training scripts for the experiments are in the file `finetune.py`.

Some examples of running the training are as follows:
```bash
# 100% Python
python3 finetune.py --language python --model_path Salesforce/codegen-350M-nl --seq_length 512 --batch_size 8 --learning_rate 1.8e-4 --num_warmup_steps 3000 --dataset_name zhensuuu/starcoderdata_100star_py --epoch 5 --output_dir ./checkpoints/

# 100% SimPy
python3 finetune.py --language spython --model_path Salesforce/codegen-350M-nl --seq_length 512 --batch_size 8 --learning_rate 1.8e-4 --num_warmup_steps 3000 --dataset_name zhensuuu/starcoderdata_100star_py --epoch 5 --output_dir ./checkpoints/ 

# Python -> 50% SimPy
python3 finetune.py --language spython_further --model_path Salesforce/codegen-350M-nl --seq_length 512 --batch_size 8 --learning_rate 1.8e-4 --num_warmup_steps 3000 --dataset_name zhensuuu/starcoderdata_100star_py --epoch 5 --output_dir ./checkpoints/100star --further_train ./checkpoints/codegen-python/best_model --ratio 0.5
```

#### Evaluation
We perform the evaluation using `bigcode-evaluation-harness` by creating a new task `humaneval_spy` in the `bigcode-evaluation-harness/bigcode_eval/tasks` folder.

Please refer to the scripts `eval_*.sh` in the `bigcode-evaluation-harness` folder for running the evaluation.

#### Others
The token counting scripts are in `token_count.py`. 
You can run the experiments by:
```
python3 token_count.py
```

The speed comparison scripts are in `speed_test.py` and `speed_analysis.py`.