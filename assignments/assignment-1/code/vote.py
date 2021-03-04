print("Hi! I would like to know your name and age!")
name = input("Name: ")
age_txt = input("Age: ")

age = int(age_txt)

if age >= 18:
	print("Hello {}! Congratulation! You are eligible to vote!".format(name))
else:
	print("Hello {}! Sorry you are eligible to vote!".format(name))
