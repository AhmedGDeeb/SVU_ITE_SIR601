// -------------------------------------------------------------------------
/* choose Corpus files or db */
const useDefaultDbCheckbox = document.getElementById("use-default-db-checkbox");
const filesInput = document.getElementById("files-input");
filesInput.required = !useDefaultDbCheckbox.checked;
const filesDiv = document.getElementById("files-div");
filesDiv.hidden = useDefaultDbCheckbox.checked;
const databasesSelectDiv = document.getElementById("database-select-div");
databasesSelectDiv.hidden = !useDefaultDbCheckbox.checked;
useDefaultDbCheckbox.addEventListener("change", (e) => {
    const filesInput = document.getElementById("files-input");
    filesInput.required = !e.currentTarget.checked;
    const filesDiv = document.getElementById("files-div");
    filesDiv.hidden = e.currentTarget.checked;
    const databasesSelectDiv = document.getElementById("database-select-div");
    databasesSelectDiv.hidden = !e.currentTarget.checked;
});

// -------------------------------------------------------------------------
/* error message */

// Get all elements with class="closebtn"
var close = document.getElementsByClassName("closebtn");
var i;

// Loop through all close buttons
for (i = 0; i < close.length; i++) {
  // When someone clicks on a close button
  close[i].onclick = function(){

    // Get the parent of <span class="closebtn"> (<div class="alert">)
    var div = this.parentElement;

    // Set the opacity of div to 0 (transparent)
    div.style.opacity = "0";

    // Hide the div after 600ms (the same amount of milliseconds it takes to fade out)
    setTimeout(function(){ div.style.display = "none"; }, 600);
  }
}

// -------------------------------------------------------------------------
