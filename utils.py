import os
import argparse

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, default="Salesforce/codegen25-7b-multi")
    parser.add_argument("--dataset_name", type=str, default="bigcode/starcoderdata")
    parser.add_argument("--language", type=str, default="python")
    parser.add_argument("--subset", type=str)
    parser.add_argument("--split", type=str)
    parser.add_argument("--ratio", type=float, default=1.0)
    parser.add_argument("--size_valid_set", type=int, default=10000)
    parser.add_argument("--streaming", action="store_true")
    parser.add_argument("--shuffle_buffer", type=int, default=5000)
    parser.add_argument("--resume_from_checkpoint", type=str, default=None)

    parser.add_argument("--seq_length", type=int, default=512)
    parser.add_argument("--epoch", type=int, default=5)
    parser.add_argument("--batch_size", type=int, default=8)
    parser.add_argument("--gradient_accumulation_steps", type=int, default=8)
    parser.add_argument("--eos_token_id", type=int, default=49152)

    parser.add_argument("--lora_r", type=int, default=16)
    parser.add_argument("--lora_alpha", type=int, default=32)
    parser.add_argument("--lora_dropout", type=float, default=0.05)

    parser.add_argument("--learning_rate", type=float, default=1.8e-4)
    parser.add_argument("--lr_scheduler_type", type=str, default="cosine")
    parser.add_argument("--num_warmup_steps", type=int, default=100)
    parser.add_argument("--weight_decay", type=float, default=0.1)
    parser.add_argument("--from_scratch", action="store_true")
    parser.add_argument("--local_rank", type=int, default=0)
    parser.add_argument("--fsdp", type=str, default=None)
    parser.add_argument("--no_fp16", action="store_false")
    parser.add_argument("--bf16", action="store_true", default=True)
    parser.add_argument("--no_gradient_checkpointing", action="store_false", default=False)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--num_workers", type=int, default=None)
    parser.add_argument("--output_dir", type=str, default="./checkpoints")
    parser.add_argument("--log_freq", default=10, type=int)
    parser.add_argument("--eval_freq", default=1, type=int)
    parser.add_argument("--save_freq", default=1, type=int)
    parser.add_argument("--further_train", default=None, type=str)

    return parser.parse_args()


def traverse_all_children(node, results):
    results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_all_children(n, results)


def count_lines(node):
    start_point = node.start_point
    end_point = node.end_point
    number_of_lines = end_point[0] - start_point[0] + 1
    return number_of_lines

def traverse_type(node, results, kind):
    if node.type == kind:
        results.append(node)
    if not node.children:
        return
    for n in node.children:
        traverse_type(n, results, kind)


def replace_from_blob(nodes, new_strs, blob):
    # replace the string of node with the new_str in the blob
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    if not isinstance(new_strs, (list, tuple)):
        new_strs = [new_strs]
    if len(nodes) == 0:
        return blob
    modifications = []
    for node, new_str in zip(nodes, new_strs):
        modifications.append({
            'start': node.start_byte,
            'end': node.end_byte,
            'new_str': new_str
        })
    modifications.sort(key=lambda x: len(x['new_str']))
    modifications_to_be_removed = []
    for i, modification in enumerate(modifications):
        for j, other_modification in enumerate(modifications[i+1:]):
            # if the modification is contained in other modification, then apply the modification in the new_str of other modification
            if other_modification['start'] <= modification['start'] and other_modification['end'] >= modification['end']:
                print('Before: ', modifications[j]['new_str'])
                modifications[j]['new_str'] = modifications[j]['new_str'][:modification['start'] - other_modification['start']] + modification['new_str'] + modifications[j]['new_str'][modification['end'] - other_modification['start']:]
                print('After: ', modifications[j]['new_str'])
                modifications_to_be_removed.append(i)
                
                break
    modifications = [modifications[i] for i in range(len(modifications)) if i not in modifications_to_be_removed]
                
    for i, modification in enumerate(modifications):
        if modification['start'] == modification['end']:
            continue
        blob = blob[:modification['start']] + modification['new_str'] + blob[modification['end']:]
        # update the start_byte and end_byte of the following nodes
        for j in range(i+1, len(modifications)):
            modifications[j]['start'] += len(modification['new_str']) - (modification['end'] - modification['start'])
            modifications[j]['end'] += len(modification['new_str']) - (modification['end'] - modification['start'])
    return blob


if __name__ == '__main__':
    from tree_sitter import Language, Parser
    Language.build_library(
        'spy/build/spython-languages.so',
        [
            './spy_grammar'
        ]
    )