from dotenv import load_dotenv
load_dotenv()

from pydantic import BaseModel, Field
from ai.llm import call_llm


class CityInfo(BaseModel):
    name: str
    country: str
    population_millions: float = Field(description="Approximate population in millions")
    famous_for: list[str] = Field(description="2-3 things this city is famous for")


result = call_llm(
    system_prompt="You are a geography expert. Give factual city information.",
    user_message="Tell me about Singapore.",
    response_model=CityInfo,
)

print(f"Type: {type(result).__name__}")
print(f"Name: {result.name}")
print(f"Country: {result.country}")
print(f"Population: {result.population_millions}M")
print(f"Famous for: {result.famous_for}")