{ "questions": [ {"id":1,"weight":2}, {"id":2,"weight":3}, {"id":3,"weight":2}, {"id":4,"weight":3}, {"id":5,"weight":3}, {"id":6,"weight":2}, {"id":7,"weight":2}, {"id":8,"weight":1}, {"id":9,"weight":2}, {"id":10,"weight":2}, {"id":11,"weight":1}, {"id":12,"weight":1}, {"id":13,"weight":1}, {"id":14,"weight":3}, {"id":15,"weight":2}, {"id":16,"weight":2}, {"id":17,"weight":3}, {"id":18,"weight":1}, {"id":19,"weight":2} ],

"scoring": { "formula": "sum(answer_score * weight) / sum(weight)", "risk_formula": "(100 - score) * weight" },

"zones": { "green": {"min":80}, "yellow": {"min":50,"max":79}, "red": {"max":49} },

"criteria": { "speed": [3,5,9,10,15], "accuracy": [4,6,11,17], "capacity": [1,2,7,16], "management": [8,12,13,14,18,19] },

"output": { "top_problems": 3, "method": "highest risk score", "include": [ "problem", "impact", "quick_fix", "limitation" ] },

"cta_logic": { "green": "оптимизация", "yellow": "разобраться", "red": "остановить потери" } }