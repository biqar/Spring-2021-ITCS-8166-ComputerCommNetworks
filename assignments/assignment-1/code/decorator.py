# Decorator function

def decorate_it(func):
	def wrapper(*args, **kwargs):
		return func(*args, **kwargs)
	return wrapper

def str_reverse(str1, str2, str3):
	rev_str1 = ''.join(reversed(str1))
	rev_str2 = ''.join(reversed(str2))
	rev_str3 = ''.join(reversed(str3))
	
	return rev_str1, rev_str2, rev_str3


s1 = input("First string: ")
s2 = input("Second string: ")
s3 = input("Third string: ")

print("Original string: {}, {}, {}".format(s1, s2, s3))

my_func = decorate_it(str_reverse)
r1, r2, r3 = my_func(s1, s2, s3)

print("Reversed string: {}, {}, {}".format(r1, r2, r3))
