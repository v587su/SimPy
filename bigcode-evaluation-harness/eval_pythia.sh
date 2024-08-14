device=$1
# raise error if no device is specified
if [ -z "$device" ]
then
    echo "Please specify a device number"
    exit 1
fi

CUDA_VISIBLE_DEVICES=$device accelerate launch main.py \
  --model pythia-1b-spython\
  --tasks humaneval_spy\
  --max_length_generation 512 \
  --temperature 0.2 \
  --top_p 0.95 \
  --n_samples 10 \
  --precision fp16 \
  --batch_size 1 \
  --allow_code_execution \
  --save_generations \
  --load_data_path ../cached \
  --save_generations_path ../results/ \
  --language spython \
  --tokenizer EleutherAI/pythia-1b

CUDA_VISIBLE_DEVICES=$device accelerate launch main.py \
  --model pythia-1b-python\
  --tasks humaneval\
  --max_length_generation 512 \
  --temperature 0.2 \
  --top_p 0.95 \
  --n_samples 10 \
  --precision fp16 \
  --batch_size 1 \
  --allow_code_execution \
  --save_generations \
  --load_data_path ../cached \
  --save_generations_path ../results/ \
  --language python \
  --tokenizer EleutherAI/pythia-1b
