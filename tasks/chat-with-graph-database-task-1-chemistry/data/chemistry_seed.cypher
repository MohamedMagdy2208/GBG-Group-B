MERGE (c:Element {symbol: "C"})
SET c.name = "Carbon";

MERGE (h:Element {symbol: "H"})
SET h.name = "Hydrogen";

MERGE (o:Element {symbol: "O"})
SET o.name = "Oxygen";

MERGE (methaneReaction:Reaction {equation: "C + 4H -> CH4"});

MERGE (methane:Compound {formula: "CH4"})
SET methane.name = "Methane";

MERGE (carbonDioxideReaction:Reaction {equation: "C + O2 -> CO2"});

MERGE (carbonDioxide:Compound {formula: "CO2"})
SET carbonDioxide.name = "Carbon Dioxide";

MATCH (c:Element {symbol: "C"}),
      (h:Element {symbol: "H"}),
      (r:Reaction {equation: "C + 4H -> CH4"}),
      (m:Compound {formula: "CH4"})
MERGE (c)-[carbonReactant:REACTANT]->(r)
SET carbonReactant.ratio = "1"
MERGE (h)-[hydrogenReactant:REACTANT]->(r)
SET hydrogenReactant.ratio = "4"
MERGE (r)-[:PRODUCT]->(m);

MATCH (c:Element {symbol: "C"}),
      (o:Element {symbol: "O"}),
      (r:Reaction {equation: "C + O2 -> CO2"}),
      (co2:Compound {formula: "CO2"})
MERGE (c)-[carbonReactant:REACTANT]->(r)
SET carbonReactant.ratio = "1"
MERGE (o)-[oxygenReactant:REACTANT]->(r)
SET oxygenReactant.ratio = "2"
MERGE (r)-[:PRODUCT]->(co2);

MERGE (:Drug {name: "Paracetamol"});

MERGE (:Drug {name: "Aspirin"});

MATCH (m:Compound {formula: "CH4"}),
      (p:Drug {name: "Paracetamol"})
MERGE (m)-[:USED_IN]->(p);

MATCH (co2:Compound {formula: "CO2"}),
      (a:Drug {name: "Aspirin"})
MERGE (co2)-[:USED_IN]->(a);

MERGE (:Disease {name: "Fever"});

MERGE (:Disease {name: "Headache"});

MATCH (p:Drug {name: "Paracetamol"}),
      (d:Disease {name: "Fever"})
MERGE (p)-[:TREATS]->(d);

MATCH (p:Drug {name: "Aspirin"}),
      (d:Disease {name: "Headache"})
MERGE (p)-[:TREATS]->(d);

MERGE (:Organism {type: "Human"});

MERGE (:Organism {type: "Mouse"});

MATCH (d:Disease {name: "Fever"}),
      (h:Organism {type: "Human"})
MERGE (d)-[:AFFECTS]->(h);

MATCH (d:Disease {name: "Headache"}),
      (m:Organism {type: "Mouse"})
MERGE (d)-[:AFFECTS]->(m);

MATCH (d:Disease {name: "Headache"}),
      (h:Organism {type: "Human"})
MERGE (d)-[:AFFECTS]->(h);

