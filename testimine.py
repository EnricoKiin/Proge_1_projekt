import random
a = [1, 2, 3]
def shuffle(jär):
    random.shuffle(jär)
    return jär
b = shuffle(a)
print(a)
print(b)