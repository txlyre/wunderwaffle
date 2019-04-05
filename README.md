# wunderwaffle
A tiny, asynchronous, multiple account «miner» for VK Coin 

# Instructions
1. Install Python >=3.7 and Node.js ==any 
2. Install Python's packages: websockets, requests, asyncio  
3. Create a file «accs.txt»
4. Fill it with accounts formatted aa «login:password»(note that first line is master account, but other are workers)  
5. Run «python wunderwaffle.py»  
6. Coins will be automatically mined by all workers and transfered to the master  

# Command line arguments
Script «wunderwaffle.py» has few command line arguments:  
- `-i` — disable the autobuy (idle_mode)  
- `-n` — disable the supporting  
- `-a val` — set the autotransfer triggering amount  

# Fixing some problems
- If you had added new acccount, but it was ignored, try remove the «save.dat» file and restart the script.  
