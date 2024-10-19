from swarm import Swarm, Agent
from swarm.types import Result
from openai import OpenAI
from duckduckgo_search import DDGS
import os,time
import json
from dotenv import load_dotenv,find_dotenv
from swarm.repl.repl import pretty_print_messages
import time
import random

load_dotenv(find_dotenv())

# 搜索函数
def search(query: str, context_variables: dict) -> Result:
    """执行 DuckDuckGo 搜索并返回结果
    
    Args:
        query: 搜索关键词
        context_variables: 上下文变量
    """
    results = context_variables.get("search_results", [])
    
    max_retries = 3
    retry_delay = 5

    if len(results) > 0:
        time.sleep(retry_delay)
    
    for attempt in range(max_retries):
        try:
            with DDGS(proxy='http://127.0.0.1:7890') as ddgs:
                new_results = list(ddgs.text(query, max_results=3))
                results.extend(new_results)
                break
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"搜索失败，正在重试（{attempt + 1}/{max_retries}）...")
                time.sleep(retry_delay + random.uniform(0, 2))
            else:
                print(f"搜索失败：{str(e)}")
                results.append({"title": "搜索失败", "body": "无法获取搜索结果，请稍后再试。"})
    
    # 将搜索结果保存到上下文中
    return Result(
        value='\n'.join(x["title"]+':'+x["body"] for x in context_variables.get("search_results", [])),
        context_variables={
            "search_results": results,
            "original_query": query
        },
        agent=analyzer_agent
    )

def transfer_to_synthesizer(context_variables: dict) -> Result:
    return Result(
       value=context_variables.get("value", ''),
       context_variables=context_variables,
       agent=synthesizer_agent,
   )

# 搜索器 Agent
searcher_agent = Agent(
    name="Searcher",
    instructions="""You are a search expert.""",
    functions=[search]
)

synthesizer_agent = Agent(
    name="Synthesizer",
    instructions="""You are a synthesis expert. Your role is to:
1. Combine analyzed information into a coherent response
2. Present information clearly and logically
3. Address the original question comprehensively
4. Acknowledge uncertainties and limitations

Your response should:
1. Be clear and well-structured
2. Cite sources when appropriate
3. Address all aspects of the original question
4. Be accurate and nuanced
5. Use language appropriate for the user's level of expertise

Maintain a balanced, objective tone while being helpful and informative."""
)
# 分析器 Agent
analyzer_agent = Agent(
    name="Analyzer",
    instructions="""Determine if you need to search again with another keyword.""",
    functions=[transfer_to_synthesizer,search]
)

def process_and_print_streaming_response(response):
    content = ""
    last_sender = ""
    function_results = []

    for chunk in response:
        if "sender" in chunk:
            last_sender = chunk["sender"]

        if "content" in chunk and chunk["content"] is not None:
            if not content and last_sender:
                print(f"\033[94m{last_sender}:\033[0m", end=" ", flush=True)
                last_sender = ""
            print(chunk["content"], end="", flush=True)
            content += chunk["content"]

        if "tool_calls" in chunk and chunk["tool_calls"] is not None:
            for tool_call in chunk["tool_calls"]:
                f = tool_call["function"]
                name = f["name"]
                if not name:
                    continue
                print(f"\033[94m{last_sender}: \033[95m{name}\033[0m()")

        if "function_call" in chunk:
            function_results.append(chunk["function_call"])

        if "delim" in chunk and chunk["delim"] == "end" and content:
            print()  # End of response message
            content = ""

        if "response" in chunk:
            return chunk["response"], function_results

    return None, function_results


# 运行示例
def run(
    starting_agent, context_variables=None, stream=False, debug=False,user_input='openai swarm'
) -> None:
    client = Swarm(OpenAI(api_key=os.getenv("OPENAI_API_KEY"),base_url=os.getenv("LLM_BASE"),))
    print("Starting Swarm CLI 🐝")

    messages = []
    agent = starting_agent

    # user_input = input("\033[90mUser\033[0m: ")
    messages.append({"role": "user", "content": user_input})

    response = client.run(
        model_override=os.getenv("MODEL"),
        agent=agent,
        messages=messages,
        context_variables=context_variables or {},
        stream=stream,
        debug=debug,
    )

    if stream:
        response = process_and_print_streaming_response(response)
    else:
        pretty_print_messages(response.messages)



# 使用示例
if __name__ == "__main__":
    run(starting_agent=searcher_agent,stream=True,debug=True,context_variables={})