from swarm import Swarm, Agent
import dotenv
dotenv.load_dotenv()

def getAgent():
    client = Swarm()
    
    def planNode(context_variables):
        object = context_variables['messages'][0]['content']
        planlist = planner.plan(object)[:5]
        return {"plan": planlist, "next_plan": planlist[0], "past_steps": []}

    def toolNode(context_variables):
        serp_response = serp.search(keywords=context_variables['next_plan'])
        past_steps = list({item['href']: item for item in context_variables['past_steps'] + serp_response}.values())
        return {"past_steps": past_steps}

    def decisionNode(context_variables):
        answer, nextPlan = decision_maker.thinkNanswer(
            input=context_variables['messages'][-1]['content'],
            plan=str(context_variables['plan']),
            current_plan=context_variables['next_plan'],
            past_steps=serp.serpResult2md(context_variables['past_steps']))
        if nextPlan is None:
            context_variables['messages'].append({'role':'assistant','content':answer})
        return {"next_plan": nextPlan}

    def should_loop(context_variables):
        if context_variables['next_plan'] is not None:
            return serpTool
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
        functions=[decisionNode, should_loop]
    )

    def run_workflow(messages):
        response = client.run(
            agent=planAgent,
            messages=messages,
            context_variables={}
        )
        while response.agent != decisionAgent or response.context_variables.get('next_plan') is not None:
            response = client.run(
                agent=response.agent,
                messages=response.messages,
                context_variables=response.context_variables
            )
        return response

    return run_workflow

if __name__ == "__main__":
    # object = "Nomardlist.com introdcution, bussiness mode, tech stack and grow story"
    # getAgent()([{'role':'user','content':object}])
    print("Swarm workflow created. Use getAgent() to run the workflow.")