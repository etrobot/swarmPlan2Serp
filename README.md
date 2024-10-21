# swarmPlan2Serp
A Plan-and-excute(search) demo with OpenAI Swarm and FastHTML.

- <strong>No function-call feature required.</strong>
- Use any LLM api that follows the OpenAI format.

```mermaid
graph TD;
	__start__([__start__]):::first
	plan_agent(Analyst)
	Search(Search)
	Synthesizer(Synthesizer)
	__end__([__end__]):::last
	__start__ --> plan_agent;
	plan_agent --> serpTool;
	serpTool --> Synthesizer;
	Synthesizer -.-> plan_agent;
	Synthesizer -.-> serpTool;
	Synthesizer -.-> __end__;	
```

## Usage

1. Copy .env_example to .env and fill out the necessary information.
2. Run ```poetry install```
3. Run ```poetry run python app.py```

## Support

[![Buy Me a Coffee](https://img.shields.io/badge/Buy%20Me%20a%20Coffee-ffdd00?style=flat&logo=buy-me-a-coffee&logoColor=black)](https://www.paypal.com/paypalme/franklin755)