import asyncio
from openai import OpenAI
from honeyhive import HoneyHiveTracer, trace, atrace

# Initialize the HoneyHive tracer
HoneyHiveTracer.init(
    api_key='dXV3cXpoZmFwb3NsY3N4N3lidmE2aQ==',
    project='openmanus-trace',
    source='test',
    session_name='OpenManus Test'
)

# Test function with tracing
@trace
def call_openai():
    client = OpenAI(api_key="your openai api key")  # Using environment variable for API key
    completion = client.chat.completions.create(
        model='gpt-4o-mini',
        messages=[{"role": "user", "content": "What is the meaning of life?"}]
    )
    print(completion.choices[0].message.content)
    return completion.choices[0].message.content

# Test async function with tracing
@atrace
async def async_call_openai():
    # Using the synchronous client for simplicity in this test
    result = call_openai()
    return result

async def main():
    print("Testing HoneyHive tracing...")
    result = await async_call_openai()
    print(f"Test completed with result: {result}")
    print("Check the HoneyHive dashboard to see the traces.")

if __name__ == "__main__":
    asyncio.run(main()) 