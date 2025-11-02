#import "@preview/cartao:0.2.0": *

#set text(
  lang: "de",
)

#show: latex
#show: perforate


#let flash-card(question, answer, hint: []) = {
  card(question, hint, answer)
}

// define your cards

= Flash Cards Title 1

#flash-card(
  [a],
  [a],
)

#flash-card(
  [b],
  [b],
)

#flash-card(
  [c],
  [c],
)

#flash-card(
  [d],
  [d],
)

#flash-card(
  [e],
  [e],
)

#flash-card(
  [f],
  [f],
)

#flash-card(
  [g],
  [g],
)

#flash-card(
  [h],
  [h],
)


