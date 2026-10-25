import pytest
from app import store, ingest

@pytest.fixture(autouse=True)
def isolated_workspace(monkeypatch,tmp_path):
    # Tests never touch the user's Supabase project or original reports.
    monkeypatch.setenv('DATABASE_URL','')
    monkeypatch.setenv('AI_PROVIDER','evidence')
    monkeypatch.setenv('EMBEDDING_PROVIDER','none')
    monkeypatch.setattr(store,'DB',tmp_path/'workspace.sqlite3')
    monkeypatch.setattr(ingest,'ROOT',tmp_path)
    store._initialized.clear()
