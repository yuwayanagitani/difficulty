# Difficulty Tag Auto-Assigner – Settings Guide

This add-on automatically rewrites difficulty tags on notes using
**VeryHard / Hard / Medium / Easy / VeryEasy**  
based on each card’s review statistics.

It also provides a function to **bulk-remove** these 5 difficulty tags.

<br><br>

# 1. Target cards (search query)

When you run the add-on from the menu, it first asks you to enter a *search query*.

- Example: `deck:Endocrinology`  
  → Only cards in the “Endocrinology” deck are processed.

- Example: `tag:Endo`  
  → Only cards with the `Endo` tag are processed.

- Empty input  
  → All cards in the collection are processed.

The syntax is **exactly the same as the Anki browser search bar**.

<br><br>

# 2. Meaning of the config.json fields

## ◆ VeryHard  
**“Too difficult – consider changing the card settings.”**

```
"very_hard_lapses_min": 5
```

```
"very_hard_ease_max_pct": 200
```

<br>

## ◆ Hard  
**“Difficult, but within an acceptable range.”**

```
"hard_lapses_min": 3
```

```
"hard_ease_max_pct": 230
```

<br>

## ◆ Easy  
**“Easy, but still acceptable.”**

```
"easy_lapses_max": 0
```

```
"easy_ivl_min": 21
```

```
"easy_ease_min_pct": 250
```

<br>

## ◆ VeryEasy  
**“Too easy – consider tightening the card settings.”**

```
"very_easy_ivl_min": 90
```

```
"very_easy_ease_min_pct": 280
```

<br><br>

# 3. Priority of judgment

1. VeryHard  
2. Hard  
3. VeryEasy  
4. Easy  
5. Medium  

The first condition that matches is used.

<br><br>

# 4. How to run

- **Tools → Auto-assign difficulty tags (5 levels)**  
- **Tools → Remove difficulty tags**
