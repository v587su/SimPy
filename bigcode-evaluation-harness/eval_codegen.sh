device=$1
# raise error if no device is specified
if [ -z "$device" ]
then
    echo "Please specify a device number"
    exit 1
fi

CUDA_VISIBLE_DEVICES=$device accelerate launch main.py \
  --model codegen-350M-nl-spython_further-1.0\
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
  --tokenizer Salesforce/codegen-350M-nl

