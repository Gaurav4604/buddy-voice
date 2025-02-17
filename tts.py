from kokoro import KPipeline
import soundfile as sf
import torch


pipeline = KPipeline(lang_code="a")  # <= make sure lang_code matches voice

# This text is for demonstration purposes only, unseen during training
text = """
"Hey There!", "I'm Buddy!", "Your Personal Assistant!"
"""


generator = pipeline(
    text, voice="af_heart", speed=1, split_pattern=r"\n+"  # <= change voice here
)
for i, (gs, ps, audio) in enumerate(generator):
    print(i)  # i => index
    print(gs)  # gs => graphemes/text
    print(ps)  # ps => phonemes
    sf.write(f"{i}.wav", audio, 24000)
