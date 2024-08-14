import pandas as pd

data = pd.read_csv('results/tokenizer_time.csv')

print(data.columns)
def get_result(d, target_list):
    time = []
    for i in target_list:
        time.append(sum([d.get(i, 0) for i in range(i-10, i+10)]))
    return time
# token_num: 0-128, 128-512, 512-2048, 2048+
# 95% of token num
print(data['hug_token_num'].quantile(0.95))
scope = [(0, 100), (100, 500), (500,2000), (2000, 5000)]


def apply_scope(x):
    for i, (start, end) in enumerate(scope):
        if x >= start and x < end:
            return i
    return len(scope)
data['hug_token_num'] = data['hug_token_num'].apply(apply_scope)
print(data['parse_time'].sum())
print(data['parse_back_time'].sum())
print(data['hug_token_time'].sum())
print(data['hug_decode_time'].sum())
d = data.groupby('hug_token_num')

print(d.mean())


