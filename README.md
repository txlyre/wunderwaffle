# wunderwaffle
A tiny, asynchronous, multiple account «miner» for VK Coin 

# Instructions
1. Install Python >=3.7  
2. Install Python's packages: websockets, requests, asyncio  
3. Create a file «accs.txt»
4. Fill it with accounts in format «login:password»(note that first line is master-account, but other are workers)  
5. Run «python wunderwaffle.py»  
6. Coins will be automatically mained by all workers and transfered to master  
