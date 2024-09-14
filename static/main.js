if (window.screen.availWidth < 600) {
//     Make formerly segregated items take
//     up the entire viewport instead
    let query
    if (location.search !== "") {
        query = location.search + "&is_small=true"
    } else {
        query = "?is_small=true"
    }

    if (!location.search.includes("is_small")) {
        window.location.replace(location.protocol + '//' + location.host + location.pathname + query)

    }
}