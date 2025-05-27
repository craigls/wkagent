from agents import Runner, RunConfig, Agent, trace
import gradio as gr
import random
import asyncio
import wanikani
from dotenv import load_dotenv

WANIKANI_MIN_SRS_LEVEL = 5
DEFAULT_MODEL = "gpt-4o-mini"

load_dotenv()


def _agent_prompt(learned_vocab: list[str]) -> str:
    # Shuffling the vocabulary seems to give better results
    shuffled_vocab = random.sample(learned_vocab, k=len(learned_vocab))

    system_prompt = f"""
        You are a Japanese kanji learning assistant.
        You are given a list of vocabulary in kanji. The student has learned the words in this vocabulary using WaniKani's SRS method. 
        You should create complex sentences by randomly selecting words from the list.
        After the student responds, give a brief reply, then add additional sentences using randomly selected words from the list. 
        Continue this loop indefinitely. 
        You should not use English unless the student asks for an explanation in English, or when you are correcting a student's grammar.
        You should give concise corrections only.
        Do not explain the vocabulary unless asked.

        Here is a comma-separated vocabulary of words to use:

        {",".join(shuffled_vocab)}
        
        Use as many words from the provided vocabulary list as possible, as the primary goal is kanji exposure.
        Do not use words outside of this list, as the student won't be able to understand them.
        However, using very basic words is OK, and these words should be written using hiragana only.
    """
    return system_prompt


def _build_vocabulary(level: int) -> list[dict]:
    # Get learned subject ids where type is kanji_vocabulary and SRS stage is "guru"
    subject_ids = [
        assignment["subject_id"]
        for (assignment_id, assignment) in wanikani.get_assignments(
            srs_stage=WANIKANI_MIN_SRS_LEVEL
        )
    ]
    # Get vocabulary up to and including <level> then filter out words that haven't been learned yet.
    return [
        kanji
        for (subject_id, kanji) in wanikani.get_subjects(level=level)
        if subject_id in subject_ids and kanji["characters"]
    ]


async def main() -> None:
    wanikani_user = wanikani.get_user()
    learned_vocab = _build_vocabulary(wanikani_user["level"])
    run_config = RunConfig(
        model=DEFAULT_MODEL,
    )

    agent = Agent(
        name="Japanese Kanji Learning Agent",
        instructions=_agent_prompt(
            learned_vocab=[word["characters"] for word in learned_vocab]
        ),
    )

    async def chat(message: str, history: list[dict]):
        with trace("Japanese Kanji Learning Agent"):
            prompt = [{"role": h["role"], "content": h["content"]} for h in history] + [
                {"role": "user", "content": message}
            ]
            result = await Runner.run(agent, input=prompt, run_config=run_config)
            yield result.final_output

    # Make an initial call to the agent and populate the output in the chat interface
    initial_message = (
        "Please write start a conversation in Japanese using the vocabulary provided."
    )
    results = [result async for result in chat(initial_message, [])]
    # Run Gradio's chat interface
    gr.ChatInterface(
        fn=chat,
        chatbot=gr.Chatbot(
            type="messages",
            value=[{"role": "assistant", "content": results[0]}],
        ),
        type="messages",
        title="Practice conversation with your Japanese kanji assistant.",
    ).launch()


if __name__ == "__main__":
    asyncio.run(main())
