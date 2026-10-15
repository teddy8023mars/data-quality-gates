import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from decimal import localcontext
from data_quality_gates import evaluate, ConfigError

ROOT=Path(__file__).resolve().parents[1]
NOW='2026-10-15T12:00:00Z'

class RetentionArithmeticTests(unittest.TestCase):
    def contract(self,tolerance=0):
        return {'version':1,'required_columns':['n','d','r'],'empty_policy':'allow',
                'checks':[{'id':'ratio','type':'ratio_consistency','numerator_column':'n',
                'denominator_column':'d','ratio_column':'r','absolute_tolerance':tolerance}]}

    def evaluate_csv(self,text,contract):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'input.csv';path.write_text(text)
            return evaluate(contract,path,NOW,temp)

    def test_ratio_exact_boundary_zero_denominator_and_bad_cells(self):
        result=self.evaluate_csv('n,d,r\n1,4,.25\n1,4,.26\n1,4,.2600000000000001\n0,2,0\n1,0,0\n1,-4,-.25\n1,NaN,.25\n,4,.25\n1,4,Inf\n',self.contract(.01))
        self.assertEqual(result['checks'][0]['rows'],[4,6,7,8,9,10])

    def test_fraction_comparison_is_independent_of_decimal_precision(self):
        with localcontext() as context:
            context.prec=2
            result=self.evaluate_csv('n,d,r\n1,3,.3333333333333333\n1,3,.5\n9007199254740993,1,9007199254740992\n',self.contract(1e-12))
        self.assertEqual(result['checks'][0]['rows'],[3,4])
        exact=self.evaluate_csv('n,d,r\n1,3,.33333333333333333333333333333333333333333333333333\n',self.contract(0))
        self.assertEqual(exact['checks'][0]['rows'],[2])

    def test_arithmetic_bounds_fail_as_quality_not_unhandled_decimal_error(self):
        result=self.evaluate_csv('n,d,r\n1e101,1,1e101\n1,1e-101,1e101\n'+'1'*101+',1,1\n',self.contract())
        self.assertEqual(result['checks'][0]['rows'],[2,3,4])

    def test_integer_flag_rejects_fraction_without_changing_numeric_range(self):
        contract={'version':1,'required_columns':['n'],'empty_policy':'allow','checks':[
            {'id':'count','type':'numeric_range','column':'n','min':0,'integer':True}]}
        result=self.evaluate_csv('n\n2\n2.0\n2e1\n2.5\nNaN\n',contract)
        self.assertEqual(result['checks'][0]['rows'],[5,6])
        contract['checks'][0]['integer']=False
        self.assertEqual(self.evaluate_csv('n\n2.5\n',contract)['status'],'passed')
        contract['checks'][0]['integer']='true'
        with self.assertRaises(ConfigError):self.evaluate_csv('n\n',contract)

    def test_ratio_bad_config_rejected_on_empty_data(self):
        for change in [{'absolute_tolerance':-1},{'absolute_tolerance':True},{'absolute_tolerance':'0.01'},
                       {'absolute_tolerance':1.1},{'absolute_tolerance':1e-101},
                       {'ratio_column':'unknown'},{'numerator_column':'d'},{'expression':'n/d'}]:
            with self.subTest(change=change):
                contract=self.contract();contract['checks'][0].update(change)
                with self.assertRaises(ConfigError):self.evaluate_csv('n,d,r\n',contract)

    def test_cli_preserves_tolerance_decimal_tokens(self):
        for token,code in [('-1e-999',2),('1.00000000000000001',2),('1e-999',2),('0.0099999999999999999',1)]:
            with self.subTest(token=token),tempfile.TemporaryDirectory() as temp:
                folder=Path(temp);contract=folder/'contract.json';data=folder/'data.csv'
                contract.write_text(json.dumps(self.contract()).replace('"absolute_tolerance": 0','"absolute_tolerance": '+token))
                data.write_text('n,d,r\n1,4,.26\n')
                proc=subprocess.run([sys.executable,'-m','data_quality_gates','--contract',str(contract),'--data',str(data),
                    '--reference-time',NOW],cwd=ROOT,env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True)
                self.assertEqual(proc.returncode,code,proc.stdout+proc.stderr)
                self.assertEqual(json.loads(proc.stdout)['status'],'config_error' if code==2 else 'failed')

    def test_strict_retention_cli_catches_bounded_wrong_rate_and_fractional_count(self):
        folder=ROOT/'examples/moba-retention'
        for name,code,counts in [('clean',0,[0]*8),('wrong-rate',1,[0,0,0,0,0,0,0,1]),
                                 ('fractional-count',1,[0,0,0,0,1,0,0,0]),('dirty',1,[0,0,0,0,0,0,1,1])]:
            with self.subTest(name=name):
                proc=subprocess.run([sys.executable,'-m','data_quality_gates','--contract',str(folder/'strict-contract.json'),
                    '--data',str(folder/(name+'.csv')),'--reference-time',NOW],cwd=ROOT,
                    env={**os.environ,'PYTHONPATH':str(ROOT/'src')},capture_output=True,text=True)
                self.assertEqual(proc.returncode,code,proc.stdout+proc.stderr)
                report=json.loads(proc.stdout)
                self.assertEqual(report['rows'],8)
                self.assertEqual([c['violations'] for c in report['checks']],counts)

if __name__=='__main__':unittest.main()
