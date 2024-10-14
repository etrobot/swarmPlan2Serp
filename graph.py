import os
from swarm import Swarm, Agent
from agents import planner, decision_maker
from tools import serp
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
from typing import TypedDict, List, Dict, Optional, AsyncGenerator
from swarm.repl import run_demo_loop

load_dotenv(find_dotenv())
client = Swarm(OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL")))

class ContextVariables(TypedDict, total=False):
    messages: List[Dict[str, str]]
    plan: List[str]
    next_plan: Optional[str]
    past_steps: List[Dict[str, str]]

def planNode(context_variables: ContextVariables) -> ContextVariables:
    object = context_variables['messages'][0]['content']
    planlist = planner.plan(object)[:5]
    return {
        "plan": planlist,
        "next_plan": planlist[0],
        "past_steps": []
    }

def toolNode(context_variables: ContextVariables) -> ContextVariables:
    serp_response = serp.search(keywords=context_variables['next_plan'])
    past_steps = list({item['href']: item for item in context_variables['past_steps'] + serp_response}.values())
    return {"past_steps": past_steps}
 
def decisionNode(context_variables: ContextVariables) -> ContextVariables:
    answer, nextPlan = decision_maker.thinkNanswer(
        input=context_variables['messages'][-1]['content'],
        plan=str(context_variables['plan']),
        current_plan=context_variables['next_plan'],
        past_steps=serp.serpResult2md(context_variables['past_steps'])
    )
    if nextPlan is None:
        context_variables['messages'].append({'role': 'assistant', 'content': answer})
    return {"next_plan": nextPlan}

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
    name="Decision Agent",
    instructions="You are a decision making agent.",
    functions=[decisionNode]
)

async def run_workflow(messages: List[Dict[str, str]]) -> AsyncGenerator[Dict[str, str], None]:
    initial_context: ContextVariables = {"messages": messages}
    response = client.run(
        model_override=os.getenv("MODEL"),
        agent=planAgent,
        messages=messages,
        context_variables=initial_context,
        debug=True,
        stream=True
    )
    
    for chunk in response:
        if "content" in chunk:
            yield {"type": "content", "data": chunk["content"]}
        elif "function_call" in chunk:
            yield {"type": "function_call", "data": chunk['function_call']['name']}
        elif "delim" in chunk:
            yield {"type": "delim", "data": chunk['delim']}
        elif "response" in chunk:
            final_response = chunk["response"]
    
    while True:
        if final_response.agent == planAgent:
            next_agent = serpTool
        elif final_response.agent == serpTool:
            next_agent = decisionAgent
        elif final_response.agent == decisionAgent:
            if final_response.context_variables.get('next_plan') is None:
                break
            next_agent = serpTool
        else:
            break

        response = client.run(
            model_override=os.getenv("MODEL"),
            agent=next_agent,
            messages=final_response.messages,
            context_variables=final_response.context_variables,
            debug=True,
            stream=True
        )

        for chunk in response:
            if "content" in chunk:
                yield {"type": "content", "data": chunk["content"]}
            elif "function_call" in chunk:
                yield {"type": "function_call", "data": chunk['function_call']['name']}
            elif "delim" in chunk:
                yield {"type": "delim", "data": chunk['delim']}
            elif "response" in chunk:
                final_response = chunk["response"]

    yield {"type": "final", "data": final_response.messages[-1]['content']}

if __name__ == "__main__":
    initial_agent = planAgent  # 或者你想要开始的任何 agent
    run_demo_loop(initial_agent, stream=True)
