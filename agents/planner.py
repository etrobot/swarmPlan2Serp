import re,os,ast
from openai import OpenAI

#prompt
plannerPrompt:str = """
For the given object, make a group of keywords for the search engine. \
for example, the object is "write a wiki for google.com",and the keywors group should be in str list format: \
["google.com funciton","google.com history","google.com tech stack","google.com bussiness mode"]

Here's the object: 

{object}

Finish it well and I will tip you $100.

"""

#output parser
def planParsed2list(output:str)->list:
    keywords_match = re.search(r'\[(.*?)\]', output.replace('\n',''))
    if keywords_match:
        keywords_str = keywords_match.group(0)  # 获取完整的方括号内容
        keywords_list = ast.literal_eval(keywords_str)
        return keywords_list
    return []

#llm
def plan(input:str) -> list:
    llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_BASE_URL"))
    prompt = plannerPrompt.format(object=input)
    result = llm.chat.completions.create(
        model=os.getenv("MODEL"),
        messages=[{'role':'user','content':prompt}]
    ).choices[0].message.content
    return planParsed2list(result)
