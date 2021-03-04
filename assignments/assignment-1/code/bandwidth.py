import re

d = { (1, 2) : "10 Mbps", (2, 3) : "5 Mbps", (3, 4) : "10 Mbps" }

def func(h1, h2):
	if (h1, h2) in d:
		return d[(h1, h2)]
	else:
		return "Not available!"

link = input("Enter the link: ")

link = link.replace('(', '').replace(')', '')
#link.strip('(\)\')
print(link)

hosts = link.split(',')
host1 = int(hosts[0])
host2 = int(hosts[1])

print("Bandwidth for link between h{} and h{} is: {}".format(host1, host2, func(host1, host2)))

