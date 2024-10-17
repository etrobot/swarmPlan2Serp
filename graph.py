from swarm import Swarm, Agent
from swarm.types import Result
from openai import OpenAI
from duckduckgo_search import DDGS
import os,time
import json
from dotenv import load_dotenv,find_dotenv
from swarm.repl.repl import process_and_print_streaming_response,pretty_print_messages
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
    print('results old:', len(results))
    
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
        value=json.dumps(results, ensure_ascii=False),
        context_variables={
            "search_results": results,
            "original_query": query
        },
        agent=analyzer_agent
    )

def analyze_results(context_variables: dict) -> Result:
    """分析搜索结果并提供见解
    
    Args:
        context_variables: 包含搜索结果的上下文变量
    """
    results = context_variables.get("search_results", [])
    return Result(
        value=json.dumps(results, ensure_ascii=False),
        agent=synthesizer_agent  # 分析完成后转交给合成者
    )

def synthesize_response(context_variables: dict) -> str:
    """合成最终回答
    
    Args:
        context_variables: 包含所有必要信息的上下文变量
    """
    return "Based on the analysis..."

# 搜索器 Agent
searcher_agent = Agent(
    name="Searcher",
    instructions="""You are a search expert. Your role is to:
1. Understand user queries and determine the best search strategy
2. Break down complex questions into searchable queries
3. Execute searches using the search() function to gather relevant information

When you receive a question:
1. First analyze if you need to break it down into multiple searches
2. For each search, formulate an effective query that will yield relevant results
3. Use the search() function to perform the search
4. Pass the results to the analyzer

Be thorough but efficient - prioritize quality over quantity in your searches.""",
    functions=[search]
)

# 分析器 Agent
analyzer_agent = Agent(
    name="Analyzer",
    instructions="""You are an analysis expert. Your role is to:
1. Review search results objectively
2. Identify key information and patterns
3. Evaluate the credibility and relevance of sources
4. Extract the most pertinent information

For each piece of information:
1. Verify it against other sources when possible
2. Note any contradictions or inconsistencies
3. Identify what additional information might be needed
4. Organize the insights logically

Focus on facts and credible information, noting any uncertainties or assumptions.""",
    functions=[analyze_results]
)

# 合成器 Agent
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

Maintain a balanced, objective tone while being helpful and informative.""",
    functions=[synthesize_response]
)


# 运行示例
def run(
    starting_agent, context_variables=None, stream=False, debug=False
) -> None:
    client = Swarm(OpenAI(api_key=os.getenv("OPENAI_API_KEY"),base_url=os.getenv("LLM_BASE"),))
    print("Starting Swarm CLI 🐝")

    messages = []
    agent = starting_agent

    while True:
        user_input = input("\033[90mUser\033[0m: ")
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

        messages.extend(response.messages)
        agent = response.agent


# 使用示例
if __name__ == "__main__":
    run(starting_agent=searcher_agent,debug=True,context_variables={})
