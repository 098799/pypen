# pypen
Super easy pen, ink and usage collection manager with json databases. Can display the data in a pretty way. Details below.

### Usage
Either run the program with no parameters and choose from the menu: `./pypen.py` or `python3 ./pypen.py` or you run it with appropriate parameters already. Available options are:
 * `./pypen.py lp` -- lists pens. Can be ordered and constrained by parameters, e.g. `./pypen.py lp Rot=1 Brand` gives you the list of pens from the top rotation ordered by `Brand`,
 * `./pypen.py li` -- lists inks,
 * `./pypen.py lu` -- lists usages,
 * `./pypen.py sp` -- statistics about pens. Can be constrained by type of statistic, e.g. `./pypen.py sp Brand`
 * `./pypen.py si` -- statistics about inks.
 * `./pypen.py su` -- statistics about usage. Should be constrained by type of statistic, e.g. `./pypen.py su Pen`, `./pypen.py su Ink`, `./pypen.py su Nib`.

As of adding and changing items, you should do it from inside the program. Run `./pypen.py` and type `ap`, `ai`, `au` or `ad` for adding pens, inks and usages: beginning and end, respectively. When it comes to adding usages, the better way is to add them right when you ink the pens or clean them by using `ab` for the beginning of usage (today) and `ae` for the cleanup.

After adding or changing something you can export it by typing `e` or safely save and quit by typing `q`. Terminating the program in any other way, e.g. `C-c` will not save the changes.
