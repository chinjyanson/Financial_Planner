import asyncio 
import random

n = 100
dict = [5 * i for i in range(n)]
async def query(request):

    status = dict[request]
    time = random.uniform(0.1, 3)
    print(f"Executing Request{request} with status: {status} for {time}s")
    await asyncio.sleep(time)  # Using a smaller sleep range for testing
    print(f"Returning Request{request} with status: {status}")
    print(f"Before:{status}, After: {dict[request]}")
    return status

async def main():

    tasks = [query(i) for i in range(n)]

    results = await asyncio.gather(*tasks)


asyncio.run(main())