from fasthtml.common import Titled, Form, Group, Input, Button, Div, H3, P, Script, EventStream, sse_message, serve, fast_app, MarkdownJS, Details, Summary, Iframe, Body, Nav, A, Main, RedirectResponse, Template, Style
# 添加 Zero_md 导入
from fasthtml.components import Zero_md
import asyncio, os, json, shortuuid
from datetime import datetime
from dotenv import load_dotenv
from Agents import Agents, analyzer_agent
# Add database functionality
from fasthtml.common import database

# Load environment variables
load_dotenv()

# Set up database
db = database("database/chats.db")
chats = db.t.chats
if chats not in db.t:
    chats.create(id=str, title=str, created=datetime, messages=bytes, pk="id")
chatDataTransferObject = chats.dataclass()

# 添加 Zero-md 的 script 标签
zeromd_headers = [Script(type="module", src="https://cdn.jsdelivr.net/npm/zero-md@3?register")]

app, rt = fast_app(hdrs=(
        Script(src="https://unpkg.com/tailwindcss-cdn@3.4.3/tailwindcss.js"), 
        Script(src="https://unpkg.com/htmx-ext-sse@2.2.1/sse.js"),
        MarkdownJS(),
        # 添加 Zero-md 的 headers
        *zeromd_headers
    )
)
messages = []

# 修改 render_md 函数
def render_md(md, css='.markdown-body {background-color: unset !important; color: unset !important;}'):
    css_template = Template(Style(css), data_append=True)
    return Zero_md(css_template, Script(md, type="text/markdown"))

# ChatMessage component
def ChatMessage(msg_idx, **kwargs):
    msg = messages[msg_idx]
    bubble_class = "bg-teal-300 bg-opacity-20 rounded-lg p-3 max-w-5xl" if msg['role'] == 'user' else 'bg-blue-400 bg-opacity-20 rounded-lg p-3 max-w-5xl'
    chat_class = "flex justify-end mb-4" if msg['role'] == 'user' else 'flex justify-start mb-4'
    return Div(
        Div(
            Div(msg['role'], cls="text-sm text-gray-600 mb-1"),
            Div(render_md(msg['content']), id=f"chat-content-{msg_idx}", cls=f"{bubble_class}", **kwargs),
            cls="flex flex-col"
        ),
        id=f"chat-message-{msg_idx}",
        cls=f"{chat_class}",
        hx_swap="beforeend show:bottom"
    )

def navigation():
    return Nav(
        H3('SwarmPlan2Serp - A OpenAI Swarm Application with FastHTML', cls="text-2xl font-bold text-white"),
        cls='m-0 bg-teal-600 p-4'
    )

def get_messages():
    return []

@rt("/")
async def get():
    return RedirectResponse(url=f"/chat/{shortuuid.uuid()}")

@rt("/chat/{id}")
async def get(id: str):
    global messages
    try:
        chat = chats[id]
        messages = json.loads(chat.messages)
    except:
        messages = []
    
    return Body(
            navigation(),
            Main(
                Div(
                    H3('Chats History', cls='font-bold my-2'),
                    *[Div(
                        A(x.title, href=f"/chat/{x.id}",cls='w-full'), 
                        P(x.created, cls='text-xs'),
                        Button("🗑", 
                   hx_delete=f"/delete-chat/{x.id}",
                   hx_target="#chats",
                   hx_swap="outerHTML",
                   cls="text-red-500 text-xs ml-2"),
            cls='py-1 flex items-center justify-between'
        ) for x in chats()],
                    id="chats",
                    cls='w-1/4 h-[85vh] overflow-y-auto border-r-2 border-gray-300 border-opacity-50 px-2'
                ),
                Div(
                    Div(
                        *[ChatMessage(x) for x in range(len(messages))],  # 添加这一行来渲染现有消息
                        id="chatlist", 
                        cls="h-[73vh] overflow-y-auto border border-gray-300 border-opacity-50 p-2 rounded-lg"
                    ),
                    Form(
                        Group(
                            A("New", href='/', cls='btn btn-secondary px-2 bg-blue-500 text-white py-2 rounded'),
                            Input(name="user_query", placeholder="Input your question here", id="msg-input", cls="w-full border rounded-lg p-2"),
                            Input(type="text", name='id', id='id-input', value=id, cls='hidden'),
                            Button(
                                "Send",
                                type="submit",
                                id="send-button",
                                cls="bg-blue-500 text-white px-4 py-2 rounded-lg hover:bg-blue-600 whitespace-nowrap",
                            )
                        ),
                        method="post", action="/send-message", 
                        hx_post="/send-message", 
                        hx_target="#chatlist", 
                        hx_swap="beforeend show:bottom",
                        hx_indicator="#send-button",
                        cls="flex space-x-2 mt-2"
                    ),
                    Div(hx_post="/send-message", hx_trigger="load", hx_target="#chatlist", hx_swap="beforeend show:bottom"),
                    cls='w-3/4 mx-2'
                ),
                cls="flex p-4 w-full mx-auto"
            )
        )

@rt("/delete-chat/{id}")
async def delete(id: str):
    chats.delete(id)
    return Div(
        H3('Chats History', cls='font-bold my-2'),
        *[Div(
            A(x.title, href=f"/chat/{x.id}"), 
            P(x.created, cls='text-xs'),
            Button("🗑", 
                   hx_delete=f"/delete-chat/{x.id}",
                   hx_target="#chats",
                   hx_swap="outerHTML",
                   cls="text-red-500 text-xs ml-2"),
            cls='py-1 flex items-center justify-between'
        ) for x in chats()],
        id="chats",
        cls='w-1/4 h-[85vh] overflow-y-auto border-r-2 border-gray-300 border-opacity-50 px-2'
    )

@rt("/send-message")
async def send_message(user_query:str, id: str):
    if not user_query:
        return

    messages.append({"role": "user", "content": user_query})
    user_msg = ChatMessage(len(messages) - 1)
    messages.append({"role": "assistant", "content": ""})
    assistant_msg = ChatMessage(
        len(messages) - 1,
        hx_ext="sse", 
        sse_connect=f"/query-stream?query={user_query}&id={id}", 
        sse_swap="message",
        hx_swap="beforeend show:bottom",
        sse_close="close",
        sse_error="close"
    )
    return (
        user_msg, 
        assistant_msg,
        Script("htmx.find('#send-button').setAttribute('disabled', 'disabled');")
    )

async def response_generator(user_query: str, id: str):
    app = Agents
    stream = app.run(
        model_override=os.getenv("MODEL"),
        agent=analyzer_agent,
        messages=messages[:-1],
        context_variables={},
        stream=True,
        debug=True,
    )
    if not user_query:
        return
    reply = ""

    try:
        for chunk in stream:
            if "content" in chunk and chunk["content"] is not None:
                reply+=chunk["content"]
                if '\n\n' in reply:
                    if reply.endswith("\n\n") and len(reply.split('\n\n'))>2:
                        yield sse_message(render_md(reply.split('\n\n')[-2]))
                else:
                    yield sse_message(chunk["content"])
            await asyncio.sleep(0)
    except Exception as e:
        yield sse_message(
           Summary(
            Details(
                P(f"Error: {str(e)}")
            )
           )
        )
    
    messages[-1]['content'] = reply
    
    # Update database
    chat = chatDataTransferObject()
    chat.title = messages[0]["content"]
    chat.created = datetime.now()
    chat.id = id
    chat.messages = json.dumps(messages)
    chats.upsert(chat)
    
    yield sse_message(
        Div(A(chat.title, href=f"/chat/{chat.id}"), P(chat.created, cls='text-xs'), cls='py-1', hx_swap_oob="beforeend show:bottom", id="chats"),
        event="update_chats"
    )
    
    yield sse_message(Script("htmx.find('#send-button').removeAttribute('disabled');"))
    yield 'event: close\ndata:\n\n'

@rt("/query-stream")
async def get(query: str, id: str):
    return EventStream(response_generator(query, id))

serve()
