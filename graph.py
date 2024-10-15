import os
from swarm import Swarm, Agent
from agents import planner, decision_maker
from tools import serp
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
from typing import TypedDict, List, Dict, Optional, AsyncGenerator
from swarm.repl import run_demo_loop
from dotenv import load_dotenv
load_dotenv(find_dotenv())


load_dotenv(find_dotenv())
client = Swarm(OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")))

class ContextVariables(TypedDict, total=False):
    messages: List[Dict[str, str]]
    plan: List[str]
    next_plan: Optional[str]
    past_steps: List[Dict[str, str]]

class Result(TypedDict, total=False):
    context_variables: ContextVariables
    agent: Agent

def planNode(context_variables: ContextVariables) -> Result:
    object = context_variables['messages'][0]['content']
    planlist = planner.plan(object)[:5]
    return Result(
        context_variables={
            "plan": planlist,
            "next_plan": planlist[0],
            "past_steps": []
        },
        agent=serpTool
    )

def toolNode(context_variables: ContextVariables) -> Result:
    serp_response = serp.search(keywords=context_variables['next_plan'])
    past_steps = list({item['href']: item for item in context_variables['past_steps'] + serp_response}.values())
    return Result(
        context_variables={"past_steps": past_steps},
        agent=decisionAgent
    )
 
def decisionNode(context_variables: ContextVariables) -> Result:
    answer, nextPlan = decision_maker.thinkNanswer(
        input=context_variables['messages'][-1]['content'],
        plan=str(context_variables['plan']),
        current_plan=context_variables['next_plan'],
        past_steps=serp.serpResult2md(context_variables['past_steps'])
    )
    if nextPlan is None:
        context_variables['messages'].append({'role': 'assistant', 'content': answer})
        return Result(context_variables={"next_plan": nextPlan})
    else:
        return Result(
            context_variables={"next_plan": nextPlan},
            agent=serpTool
        )

def should_loop(context_variables: ContextVariables) -> Optional[str]:
    if context_variables['next_plan'] is not None:
        return 'serpTool'
    else:
        return None

planAgent = Agent(
    name="Plan Agent",
    instructions="You are a planning agent.",
    functions=[planNode]
)

serpTool = Agent(
    name="SERP Tool",
    instructions="You are a search tool.",
    functions=[toolNode]
)

decisionAgent = Agent(
    name="Decision Maker",
    instructions="You are a decision making agent.",
    functions=[decisionNode]
)

async def run_workflow(
    starting_agent,
    context_variables: Optional[ContextVariables] = None,
    stream: bool = False,
    debug: bool = False
) -> AsyncGenerator[Dict[str, str], None]:
    messages = []
    agent = starting_agent
    context_variables = context_variables or {}

    while True:
        response = client.run(
            model_override=os.getenv("MODEL"),
            agent=agent,
            messages=messages,
            context_variables=context_variables,
            debug=debug,
            stream=stream
        )
        
        for chunk in response:
            print(chunk)
            if "content" in chunk:
                yield {"type": "content", "data": chunk["content"]}
            elif "delim" in chunk:
                yield {"type": "delim", "data": chunk['delim']}
            elif "response" in chunk:
                final_response = chunk["response"]
        
        messages.extend(final_response.messages)
        context_variables = final_response.context_variables
        
        if final_response.agent:
            agent = final_response.agent
        else:
            break

    yield {"type": "final", "data": messages[-1]['content']}

# 修改主函数以使用新的run_workflow
if __name__ == "__main__":
    initial_agent = planAgent
    initial_message = {'role': 'user', 'content': 'tell me about openai swarm'}
    
    async def main():
        async for chunk in run_workflow(initial_agent, context_variables={"messages": [initial_message]}, stream=True, debug=True):
            if chunk["type"] == "content":
                print(f"\033[94m助手\033[0m: {chunk['data']}", end="", flush=True)
            elif chunk["type"] == "function_call":
                print(f"\n\033[93m函数调用\033[0m: {chunk['data']}")
            elif chunk["type"] == "delim":
                print(f"\n\033[92m分隔符\033[0m: {chunk['data']}")
            elif chunk["type"] == "final":
                print(f"\n\033[91m最终响应\033[0m: {chunk['data']}")

    import asyncio
    asyncio.run(main())
