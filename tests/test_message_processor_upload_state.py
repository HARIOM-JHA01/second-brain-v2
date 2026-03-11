from src.agente_rolplay import message_processor as mp


class FakeRedis:
    def __init__(self):
        self.kv = {}
        self.sets = {}

    def exists(self, key):
        return key in self.kv

    def get(self, key):
        return self.kv.get(key)

    def set(self, key, value, ex=None):
        self.kv[key] = value

    def delete(self, key):
        self.kv.pop(key, None)

    def sadd(self, key, value):
        self.sets.setdefault(key, set()).add(value)

    def scard(self, key):
        return len(self.sets.get(key, set()))


def test_inventory_query_guard():
    assert mp.is_knowledge_base_inventory_query(
        "how many files are there in knowledge base"
    )
    assert mp.is_knowledge_base_inventory_query(
        "How many fi;les are there in knowledgebase"
    )
    assert not mp.detect_file_upload_intent(
        "how many files are there in knowledge base", "15551234567"
    )


def test_knowledge_base_count_message_from_redis_set():
    fake_redis = FakeRedis()
    fake_redis.sadd("all_uploaded_files", "a.pdf")
    fake_redis.sadd("all_uploaded_files", "b.jpg")
    msg = mp.get_knowledge_base_count_message(fake_redis, "en")
    assert msg == "There are currently 2 file(s) in the Knowledge Base."


def test_image_upload_clears_pending_flag(monkeypatch, tmp_path):
    fake_redis = FakeRedis()
    phone = "15551234567"
    fake_redis.set(f"file_upload_pending:{phone}", "pending")

    temp_file = tmp_path / "image.jpg"
    temp_file.write_bytes(b"fake")

    monkeypatch.setattr(
        mp, "extract_phone_from_twilio", lambda from_number: "15551234567"
    )
    monkeypatch.setattr(mp, "send_twilio_message", lambda *args, **kwargs: {"success": True})
    monkeypatch.setattr(mp, "download_document_from_twilio", lambda **kwargs: str(temp_file))
    monkeypatch.setattr(
        mp,
        "upload_file_to_cloudinary",
        lambda *args, **kwargs: {"success": True, "secure_url": "https://example.com/f.jpg"},
    )

    form_data = {
        "From": "whatsapp:+15551234567",
        "To": "whatsapp:+10000000000",
        "Body": "",
        "MessageSid": "SM_IMAGE_1",
        "NumMedia": "1",
        "MediaUrl0": "https://twilio.test/image",
        "MediaContentType0": "image/jpeg",
    }

    result = mp.process_incoming_messages(form_data, redis_client=fake_redis)

    assert result == "ImageProcessed"
    assert fake_redis.get(f"file_upload_pending:{phone}") is None
