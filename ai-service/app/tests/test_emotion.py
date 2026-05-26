# app/tests/test_emotion.py

from app.emotions.emotion_service import EmotionClass


def main():
    service = EmotionClass()

    test_cases = [
        "Hello, how are you doing?",
        "I'm so happy today! I finally finished my project!",
        "This is so annoying. Nothing works and I'm really frustrated.",
        "I feel very sad and tired recently. I don't know what to do.",
        "Thanks! You are really helpful.",
    ]

    for text in test_cases:
        result = service.sense(text)

        print("=" * 60)
        print("Input:", text)
        print("Emotion result:", result)

        # 如果 result 是 Pydantic model，可以这样打印成 dict
        if hasattr(result, "model_dump"):
            print("As dict:", result.model_dump())


if __name__ == "__main__":
    main()