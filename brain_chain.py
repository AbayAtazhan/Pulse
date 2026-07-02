from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
prompt = ChatPromptTemplate.from_messages([
 ("system", "You are a friendly Python tutor. Reply with ONE question only."),
 ("human", "Write a short beginner question about {topic}."),
])
chain = prompt | llm | StrOutputParser() # prompt -> model -> plain string
print(chain.invoke({"topic": "dictionaries"}))
print(chain.invoke({"topic": "for loops"}))
