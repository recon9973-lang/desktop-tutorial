const express = require('express'),
app = express(),
path = require('path'),
port = process.env.PORT || 3000,
_v = app.listen(port, _ => console.log(`Start : ${port}`));

app.use(express.json());
app.use(express.urlencoded({extended: false}));

app.post('/', (req,res) => res.redirect("/com?data="+req.body.roadFullAddr));

app.get('/com', (req,res) => res.sendFile(path.join(__dirname, './ad.html')));
