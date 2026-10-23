from app.agent_harness import CivicHarness
from app.schemas import Draft
from app.skill_loader import load_skill
from app.permissions import require,PermissionDenied
from app.duplicate_detection import find_duplicates
import pytest
class FakeAdapter:
    def generate(self,system,user):return '{"category":"grievance","summary":"Broken streetlight","location":null,"missing_fields":[],"language":"english","confidence":0.92}'
def test_skill():assert load_skill()['metadata']['name']=='civic-request-intake'
def test_model_path():
    r=CivicHarness(FakeAdapter()).intake('Broken streetlight near park')
    assert r['mode']=='open-weight' and r['draft'].category=='grievance' and 'location' in r['draft'].missing_fields
def test_permissions():
    with pytest.raises(PermissionDenied):require('citizen','update')
def test_duplicate():
    d=Draft(category='grievance',summary='Broken streetlight sector 22',location='Sector 22')
    cases=[{'id':'DEMO-123','category':'grievance','summary':'Broken streetlight sector 22','location':'Sector 22'}]
    assert find_duplicates(d,cases)[0]['id']=='DEMO-123'
def test_fallback():
    class Broken:
        def generate(self,*args):raise ValueError('offline')
    r=CivicHarness(Broken()).intake('water leakage near sector 22')
    assert r['mode']=='safe-fallback' and r['draft'].category=='water_sewage'
def test_schema_rejects_invalid_category():
    with pytest.raises(Exception):Draft(category='not-a-category',summary='test')
