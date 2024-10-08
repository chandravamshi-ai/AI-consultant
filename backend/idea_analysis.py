import os
import logging
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import requests
from typing import Dict, List
import json

app = FastAPI()

def load_api_key():
    try:
        load_dotenv()
        api_key = os.getenv("API_KEY")
        if not api_key:
            raise ValueError("API key not found. Please add your API_KEY to the .env file.")
        return api_key
    except Exception as e:
        raise RuntimeError(f"Error loading API key: {e}")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Initialize OpenAI client
api_key = load_api_key()
base_url = "https://api.aimlapi.com"
client = OpenAI(api_key=api_key, base_url=base_url)

class AnalysisRequest(BaseModel):
    domain: str
    problem: str
    website: str
    mvp:str


class ProductBriefRequest(BaseModel):
    context: Dict



@app.post("/prompt_to_json")
async def prompt_to_json(request: AnalysisRequest):
    """
    Endpoint to generate a structured JSON response based on the given domain and problem.
    """
    try:
        user_prompt = f"""
        I'm trying to create an app related to {request.domain}. The problem it solves is: {request.problem}. The website of the business is {request.website}.
        The minimum viable product is {request.mvp}

        Provide a structured response in JSON format with the following keys:
        "industry": What is the industry of the desired project?
        "product": What is the product?
        "website": What is the website of the business?
        "minimum_viable_product": What is the minimum viable product?
   

        If there isn't enough information to answer these questions, write "not enough information".
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=500,
        )

        if response and response.choices:
            message = response.choices[0].message.content
            try:
                structured_response = eval(message)  # Assuming the response is a JSON-like string
            except:
                structured_response = {"error": "Invalid JSON response from the API."}
        else:
            structured_response = {"error": "No response received from the API. Please check the input or try again later."}

        return structured_response
    except Exception as e:
        logging.error(f"Error occurred while getting response from API: {e}")
        raise HTTPException(status_code=500, detail=f"Error occurred while getting response from API: {e}")



@app.post("/generate_product_brief")
async def generate_product_brief(request: ProductBriefRequest):
    """
    Endpoint to generate a product brief based on the website overview and JSON context from prompt_to_json.
    """
    try:
        context = request.context
        user_prompt = f"""
        You are an experienced product manager creating a product brief. Use the following context and additional context to generate the brief.

        Context:
        {json.dumps(context, indent=2)}



        STEP 1: Question Analysis and Ordering
        First analyze these questions from the product brief template:
        - Who are we solving this problem for?
        - What specific problem are we trying to solve?
        - How does this problem impact our users or business?
        - Why is this problem important to solve now?
        - What evidence demonstrates this is a real and significant problem?
        - How will we know if we've successfully solved this problem?
        - How does solving this problem align with our broader goals or strategy?
        - At a high level, what approach are we considering to solve this problem?
        - What are the key components or features of this solution?
        - What specific metrics or outcomes will indicate success?
        - What are the biggest unknowns or challenges we anticipate?
        - Are there any potential negative impacts we should be aware of?
        - What are the immediate next steps to validate or refine this proposal?
        - Who needs to be involved in the next phase of this project?

        STEP 2: Answer the logically ordered questions using only the provided context:
        - Think step-by-step through each answer
        - Skip questions that cannot be reasonably answered with given context
        - Do not make up or hallucinate information
        - Be clear and concise
        - Show your thinking process for each answer

        STEP 3: Create a final product brief using EXACTLY this template structure:

        1-Pager: [Project Name]

        Problem Statement
        * What specific problem are we trying to solve?
        * How does this problem impact our users or business?

        Target Audience
        * Who are we solving this problem for?
        * (If applicable: what key characteristics define this audience/how are they distinct?)

        Why It Matters
        * Why is this problem important to solve now?
        * What evidence do we have that this is a real and significant problem?
        * How does solving this problem align with our broader goals or strategy?

        Proposed Solution
        * At a high level, what approach are we considering to solve this problem?
        * What are the key components or features of this solution?

        Success Criteria
        * How will we know if we've successfully solved this problem?
        * (If applicable: What metrics or outcomes will indicate success?)

        Risks and Considerations
        * What are the biggest unknowns or challenges we anticipate?
        * Are there any potential negative impacts we should be aware of?

        Next Steps
        * What are the immediate next steps to validate or refine this proposal?
        * Who needs to be involved in the next phase of this project?

        Additional Notes
        * Any other clear decisions made or important information relevant to the engineering, design, and/or marketing teams.
        """

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=8000,
        )

        if response and response.choices:
            message = response.choices[0].message.content
        else:
            message = "No response received from the API. Please check the input or try again later."

        return json.loads(message)
    except Exception as e:
        logging.error(f"Error occurred while generating product brief: {e}")
        raise HTTPException(status_code=500, detail=f"Error occurred while generating product brief: {e}")


@app.post("/complete_analysis")
async def complete_analysis(request: AnalysisRequest):
    """
    Endpoint that combines both prompt_to_json and generate_product_brief into a single flow.
    """
    try:
        # Get the JSON analysis
        json_response = await prompt_to_json(request)

        if "error" in json_response:
            return json_response

        # Create the product brief request using the direct response
        brief_request = ProductBriefRequest(
            context=json_response,  # Use the response directly
            website_overview=request.website
        )

        # Generate the product brief
        product_brief = await generate_product_brief(brief_request)

        return {
            "analysis": json_response,
            "product_brief": product_brief
        }
    except Exception as e:
        logging.error(f"Error occurred in complete analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)