import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv('/root/upwork-agent/.env')
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def write_proposal(job_title, job_description, budget):
    prompt = f"""
You are an expert freelancer specializing in n8n workflows and AI automation.
Write a highly personalized, professional proposal for this job.

Job Title: {job_title}
Job Description: {job_description}
Budget: {budget}

Write a proposal that:
1. Starts with a strong hook specific to their problem
2. Shows you understand exactly what they need
3. Briefly mentions your n8n and AI automation experience
4. Proposes a clear solution
5. Ends with a confident call to action

Keep it under 200 words. Write in English. Be conversational, not robotic.
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    test_job = {
        "title": "n8n Workflow Expert needed for AI automation",
        "description": "We need someone to build automated workflows connecting our CRM with email, Slack, and AI processing. Long term work available.",
        "budget": "$500 - $1500"
    }
    print("✍️ بنكتب Proposal...")
    print("=" * 60)
    proposal = write_proposal(test_job["title"], test_job["description"], test_job["budget"])
    print(proposal)
    print("=" * 60)
    print("✅ Proposal Writer شغال!")
