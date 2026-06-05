"""
Inspiration library. Curated to your stated preference:
no Ronnie Coleman, no "beast mode", no aesthetic-obsessed gym culture.

Sources lean toward:
- Stoic & philosophical (Marcus Aurelius, Seneca, Epictetus)
- Health-as-foundation framing
- Athletes & creators with balance
- The work itself as the reward
"""
import random


THOUGHTS = [
    # Stoic
    "At dawn, when you have trouble getting out of bed, tell yourself: I have to go to work — as a human being. — Marcus Aurelius",
    "We suffer more often in imagination than in reality. — Seneca",
    "It is not death that a man should fear, but he should fear never beginning to live. — Marcus Aurelius",
    "First say to yourself what you would be; and then do what you have to do. — Epictetus",

    # Health-as-foundation
    "The body is the vehicle for everything else you want to do.",
    "Today's session isn't about the mirror. It's about being able to think clearly tomorrow, sleep well tonight, and walk up stairs at 70.",
    "Strong legs don't make you a bodybuilder. They make you someone whose blood sugar behaves and whose heart works less hard.",
    "You're not training to look impressive. You're training so the rest of your life is easier.",

    # The work itself
    "Discipline is just memory of what you wanted.",
    "You don't have to feel like it. You just have to start.",
    "The hardest part is the door of the gym. After that, the body knows what to do.",
    "Show up imperfectly rather than don't show up perfectly.",
    "Every set you log is a vote for the kind of person you're becoming.",

    # Athletes/creators with balance
    "Most people stop when they get tired. The ones who improve stop when they're done. — paraphrasing what David Goggins gets right (without the rest).",
    "The runner who runs to think clearly will keep running long after the one who runs to look good has stopped. — Murakami, paraphrased",

    # Identity-based
    "You are someone who trains four days a week. Today is a four-day-a-week day.",
    "The version of you who shows up consistently isn't a fantasy. He's already shown up — that's why you're here.",

    # Reframe missed days
    "Yesterday is closed. Today is open. That's the only math that matters.",
    "A missed day is not a verdict. It's a data point.",

    # Process
    "Slow progress is still progress, and it's the only kind that lasts.",
    "Small, boring, repeated. That's the entire trick.",
]


def pick_thought() -> str:
    return random.choice(THOUGHTS)


def pick_thoughts(n: int = 3) -> list[str]:
    return random.sample(THOUGHTS, min(n, len(THOUGHTS)))
