# Makefile for P02 LaTeX build
# Usage:
#   make          — build PDF
#   make clean    — remove build artifacts
#   make arxiv    — create arXiv submission tarball

TEX    = main
LATEX  = pdflatex
BIBTEX = bibtex

.PHONY: all clean arxiv watch

all: $(TEX).pdf

$(TEX).pdf: $(TEX).tex body.tex references.bib
	$(LATEX) $(TEX)
	$(BIBTEX) $(TEX)
	$(LATEX) $(TEX)
	$(LATEX) $(TEX)

# Use latexmk for continuous builds
watch:
	latexmk -pdf -pvc $(TEX).tex

clean:
	rm -f $(TEX).{aux,bbl,blg,log,out,toc,pdf,fls,fdb_latexmk,synctex.gz}
	rm -f *.aux

# Create arXiv-compatible tarball
arxiv: $(TEX).pdf
	tar czf p02-mapper-arxiv.tar.gz $(TEX).tex body.tex $(TEX).bbl figures/*.pdf
